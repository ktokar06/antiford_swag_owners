from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core import telecom
from core.models.call import InvalidCdrRow
from core.models.feature import NumberFeature
from core.models.subscriber import PhoneNumber, Subscriber
from core.schemas.number import (
    InvalidReasonRow,
    InvalidReasonsOut,
    NumberListOut,
    NumberOut,
    SubscriberAggOut,
    SubscriberAggRow,
)
from core.utils.pagination import digits_only, page, resolve_offset

SORTS = {
    "max_risk_score": func.coalesce(NumberFeature.max_risk_score, 0),
    "total_calls": func.coalesce(NumberFeature.total_calls, 0),
    "calls_per_hour": func.coalesce(NumberFeature.calls_per_hour, 0),
    "unique_counterparts": func.coalesce(NumberFeature.unique_counterparts, 0),
    "last_seen": PhoneNumber.last_seen,
    "number": PhoneNumber.number,
}


def mask_imsi(imsi: str | None) -> str | None:
    if not imsi:
        return None
    imsi = imsi.strip()
    return f"IMSI •••{imsi[-4:]}"


def _to_out(n: PhoneNumber, f: NumberFeature | None, imsi: str | None) -> NumberOut:
    return NumberOut(
        id=n.id,
        number=n.number.strip(),
        subscriber=mask_imsi(imsi),
        region=telecom.region_name(n.region_code),
        operator=telecom.operator_name(n.operator_code),
        kind=n.kind,
        is_valid=n.is_valid,
        invalid_reason=n.invalid_reason,
        has_incoming=f.has_incoming if f else False,
        has_outgoing=f.has_outgoing if f else False,
        has_forwarded=f.has_forwarded if f else False,
        has_fan_pattern=f.has_fan_pattern if f else False,
        fan_group=f.fan_group if f else None,
        total_calls=f.total_calls if f else 0,
        outgoing_calls=f.outgoing_calls if f else 0,
        calls_per_hour=f.calls_per_hour if f else 0,
        unique_counterparts=f.unique_counterparts if f else 0,
        region_reach=f.region_reach if f else 0,
        short_call_share=float(f.short_call_share) if f else 0,
        unanswered_share=float(f.unanswered_share) if f else 0,
        numbers_per_subscriber=f.numbers_per_subscriber if f else 1,
        max_risk_score=f.max_risk_score if f else 0,
        avg_risk_score=float(f.avg_risk_score) if f else 0,
        window_days=f.window_days if f else 0,
        first_seen=n.first_seen,
        last_seen=n.last_seen,
    )


def _base(*cols):
    return (
        select(*cols)
        .select_from(PhoneNumber)
        .join(NumberFeature, NumberFeature.phone_number_id == PhoneNumber.id, isouter=True)
        .join(Subscriber, Subscriber.id == PhoneNumber.subscriber_id, isouter=True)
    )


def _apply_filters(stmt, f: dict):
    if f.get("is_valid") is not None:
        stmt = stmt.where(PhoneNumber.is_valid == f["is_valid"])
    for flag in ("has_fan_pattern", "has_incoming", "has_outgoing", "has_forwarded"):
        if f.get(flag):
            stmt = stmt.where(getattr(NumberFeature, flag).is_(True))
    if f.get("min_score") is not None:
        stmt = stmt.where(func.coalesce(NumberFeature.max_risk_score, 0) >= f["min_score"])
    digits = digits_only(f.get("search_digits") or f.get("search_text"))
    if digits:
        stmt = stmt.where(or_(PhoneNumber.number.like(f"%{digits}%"), Subscriber.external_id.like(f"%{digits}%")))
    elif f.get("search_text"):
        q = f["search_text"].strip().lower()
        codes = {c for c in telecom.HOME_CODES
                 if q in (telecom.region_name(c) or "").lower() or q in (telecom.operator_name(c) or "").lower()}
        stmt = stmt.where(PhoneNumber.region_code.in_(codes) if codes else False)
    return stmt


def list_numbers(db: Session, f: dict) -> NumberListOut:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    sort = f.get("sort") or "-max_risk_score"
    col = SORTS.get(sort.lstrip("-"))
    if col is None:
        raise HTTPException(422, f"Недопустимая сортировка: {sort}")
    order = col.desc().nullslast() if sort.startswith("-") else col.asc().nullsfirst()
    stmt = _apply_filters(_base(PhoneNumber, NumberFeature, Subscriber.external_id), f)
    stmt = stmt.order_by(order, PhoneNumber.id.desc()).offset(offset).limit(limit + 1)
    rows, next_cursor, has_more = page(db.execute(stmt).all(), limit, offset)
    return NumberListOut(items=[_to_out(n, fr, imsi) for n, fr, imsi in rows],
                         next_cursor=next_cursor, has_more=has_more, offset=offset)


def count_numbers(db: Session, f: dict) -> int:
    return int(db.scalar(_apply_filters(_base(func.count()), f)) or 0)


def get_number(db: Session, number_id: int) -> NumberOut:
    row = db.execute(_base(PhoneNumber, NumberFeature, Subscriber.external_id)
                     .where(PhoneNumber.id == number_id)).first()
    if row is None:
        raise HTTPException(404, "Номер не найден")
    return _to_out(*row)


def aggregate_by_subscriber(db: Session) -> SubscriberAggOut:
    rows = db.execute(
        select(Subscriber.external_id, func.count(PhoneNumber.id))
        .join(PhoneNumber, PhoneNumber.subscriber_id == Subscriber.id)
        .group_by(Subscriber.external_id)
        .having(func.count(PhoneNumber.id) > 1)
        .order_by(func.count(PhoneNumber.id).desc())
        .limit(20)
    ).all()
    return SubscriberAggOut(rows=[SubscriberAggRow(subscriber=mask_imsi(i) or "—", count=int(c)) for i, c in rows])


def aggregate_invalid_reasons(db: Session) -> InvalidReasonsOut:
    """Причины невалидности исходных записей CDR (invalid_cdr_row)."""
    rows = db.execute(
        select(func.coalesce(InvalidCdrRow.error_code, "legacy"), func.min(InvalidCdrRow.reason), func.count())
        .group_by(func.coalesce(InvalidCdrRow.error_code, "legacy"))
        .order_by(func.count().desc())
    ).all()
    return InvalidReasonsOut(rows=[
        InvalidReasonRow(code=code, invalid_reason=_reason_label(code, sample), count=int(c))
        for code, sample, c in rows
    ])


def _reason_label(code: str, sample: str | None) -> str:
    from etl.cdr_parser import ERROR_LABELS
    return ERROR_LABELS.get(code) or sample or "причина не указана"
