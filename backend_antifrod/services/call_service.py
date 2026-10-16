from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core.models.call import CallRecord
from core.models.review import CallReview
from core.models.scoring import CallDecision, CallRiskFactor, ScoringRule
from core.models.stats import StatsDaily
from core.models.subscriber import PhoneNumber
from core.models.user import AppUser
from core.schemas.call import CallAggregateByDayOut, CallAggregateByDayRow, CallListOut, CallOut, FactorOut
from core.utils.pagination import digits_only, page, resolve_offset

REVIEW_STATUSES = {"pending", "confirmed_fraud", "false_positive", "cleared"}
DECISIONS = {"allow", "review", "auto_blocked"}

SORTS = {
    "risk_score": (func.coalesce(CallDecision.risk_score, 0), CallRecord.id),
    "started_at": (CallRecord.started_at, CallRecord.id),
    "duration_sec": (CallRecord.duration_sec, CallRecord.id),
    "id": (CallRecord.id,),
}


def _to_out(call: CallRecord, decision: CallDecision | None, review: CallReview | None,
            factors: list[tuple[CallRiskFactor, ScoringRule]], number_ref: int | None = None) -> CallOut:
    return CallOut(
        id=call.id,
        caller=call.caller_number,
        callee=call.callee_number,
        forward=call.forward_number,
        type=call.type,
        imsi=call.imsi,
        cdr_file_id=call.cdr_file_id,
        started_at=call.started_at,
        duration_sec=call.duration_sec,
        direction=call.direction,
        connection_type=call.connection_type,
        time_bucket=call.time_bucket,
        source_country=call.source_country,
        source_operator=call.source_operator,
        foreign_origin=call.foreign_origin,
        hung_up_first_second=call.hung_up_first_second,
        is_valid=call.is_valid,
        invalid_reason=call.invalid_reason,
        number_ref=number_ref,
        number_label=call.caller_number,
        counterpart=call.callee_number,
        risk_score=decision.risk_score if decision else 0,
        decision=decision.decision if decision else "unscored",
        probability=decision.probability if decision else None,
        model_version=decision.model_version if decision else None,
        review_status=review.status_code if review else "pending",
        assigned_to=review.assigned_to if review else None,
        reviewed_by=review.reviewed_by if review else None,
        reviewed_at=review.reviewed_at if review else None,
        review_note=review.review_note if review else None,
        risk_factors=[
            FactorOut(
                code=rule.code, label=rule.label, group=rule.factor_group, detail=cf.detail,
                base_points=rule.base_points, weight=float(rule.weight), enabled=rule.enabled, points=cf.points,
            )
            for cf, rule in sorted(factors, key=lambda x: -x[0].points)
        ],
    )


def _factors_for(db: Session, call_ids: list[int]) -> dict[int, list]:
    out: dict[int, list] = {cid: [] for cid in call_ids}
    if not call_ids:
        return out
    rows = db.execute(
        select(CallRiskFactor, ScoringRule)
        .join(ScoringRule, ScoringRule.id == CallRiskFactor.rule_id)
        .where(CallRiskFactor.call_id.in_(call_ids))
    ).all()
    for cf, rule in rows:
        out[cf.call_id].append((cf, rule))
    return out


def _phone_ids(db: Session, numbers: set[str]) -> dict[str, int]:
    if not numbers:
        return {}
    return {n.strip(): i for n, i in db.execute(
        select(PhoneNumber.number, PhoneNumber.id).where(PhoneNumber.number.in_(numbers))
    ).all()}


def build_outs(db: Session, rows) -> list[CallOut]:
    calls = list(rows)
    factors = _factors_for(db, [c.id for c, _, _ in calls])
    phones = _phone_ids(db, {c.caller_number for c, _, _ in calls})
    return [_to_out(c, d, r, factors[c.id], phones.get(c.caller_number)) for c, d, r in calls]


def _base_select(*cols):
    return (
        select(*cols)
        .select_from(CallRecord)
        .join(CallDecision, CallDecision.call_id == CallRecord.id, isouter=True)
        .join(CallReview, CallReview.call_id == CallRecord.id, isouter=True)
    )


def _apply_filters(db: Session, stmt, f: dict):
    if f.get("decision"):
        if f["decision"] not in DECISIONS:
            raise HTTPException(422, "Неизвестное решение")
        if f["decision"] == "allow":
            stmt = stmt.where(or_(CallDecision.decision == "allow", CallDecision.call_id.is_(None)))
        else:
            stmt = stmt.where(CallDecision.decision == f["decision"])
    if f.get("review_status"):
        if f["review_status"] == "pending":
            stmt = stmt.where(or_(CallReview.status_code == "pending", CallReview.call_id.is_(None)))
        else:
            stmt = stmt.where(CallReview.status_code == f["review_status"])
    if f.get("direction"):
        stmt = stmt.where(CallRecord.direction == f["direction"])
    if f.get("is_valid") is not None:
        stmt = stmt.where(CallRecord.is_valid == f["is_valid"])
    if f.get("foreign_origin"):
        stmt = stmt.where(CallRecord.foreign_origin.is_(True))
    if f.get("cdr_file_id"):
        stmt = stmt.where(CallRecord.cdr_file_id == f["cdr_file_id"])
    if f.get("type"):
        stmt = stmt.where(CallRecord.type == f["type"])
    if f.get("date_from"):
        stmt = stmt.where(CallRecord.started_at >= f["date_from"])
    if f.get("date_to"):
        stmt = stmt.where(CallRecord.started_at < f["date_to"])
    if f.get("min_score") is not None:
        stmt = stmt.where(func.coalesce(CallDecision.risk_score, 0) >= f["min_score"])
    if f.get("number_ref"):
        number = db.scalar(select(PhoneNumber.number).where(PhoneNumber.id == f["number_ref"]))
        if number is None:
            return stmt.where(False)
        stmt = stmt.where(or_(CallRecord.caller_number == number, CallRecord.callee_number == number,
                              CallRecord.forward_number == number))
    digits = digits_only(f.get("search"))
    if digits:
        stmt = stmt.where(or_(
            CallRecord.caller_number.like(f"%{digits}%"),
            CallRecord.callee_number.like(f"%{digits}%"),
            CallRecord.forward_number.like(f"%{digits}%"),
        ))
    return stmt


def _order(sort: str):
    desc = sort.startswith("-")
    cols = SORTS.get(sort.lstrip("-"))
    if cols is None:
        raise HTTPException(422, f"Недопустимая сортировка: {sort}")
    return [c.desc() if desc else c.asc() for c in cols]


def list_calls(db: Session, f: dict) -> CallListOut:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    stmt = _apply_filters(db, _base_select(CallRecord, CallDecision, CallReview), f)
    stmt = stmt.order_by(*_order(f.get("sort") or "-risk_score")).offset(offset).limit(limit + 1)
    rows, next_cursor, has_more = page(db.execute(stmt).all(), limit, offset)
    return CallListOut(items=build_outs(db, rows), next_cursor=next_cursor, has_more=has_more, offset=offset)


def count_calls(db: Session, f: dict) -> int:
    stmt = _apply_filters(db, _base_select(func.count()), f)
    return int(db.scalar(stmt) or 0)


def aggregate_by_day(db: Session) -> CallAggregateByDayOut:
    rows = db.execute(select(StatsDaily).order_by(StatsDaily.day)).scalars().all()
    return CallAggregateByDayOut(rows=[
        CallAggregateByDayRow(day=str(r.day), count=r.call_count, blocked=r.blocked, review=r.review, allow=r.allow)
        for r in rows
    ])


def get_call(db: Session, call_id: int) -> CallOut:
    row = db.execute(_base_select(CallRecord, CallDecision, CallReview).where(CallRecord.id == call_id)).first()
    if row is None:
        raise HTTPException(404, "Вызов не найден")
    out = build_outs(db, [row])[0]
    decision = row[1]
    if decision and decision.feature_values:
        from core.config import settings
        from services.ml_service import get_predictor
        from ml.explain import explain_features
        from ml.feature_labels import LABELS
        import pandas as pd
        predictor = get_predictor(settings.ml_model_dir)
        if decision.model_version == predictor.metadata["model_sha256"]:
            features = pd.DataFrame([decision.feature_values], columns=predictor.feature_columns)
            explanation = explain_features(predictor.model, features)[0]
            for factor in explanation["factors"]:
                factor["label"] = LABELS.get(factor["feature"], factor["feature"])
                factor["value"] = features.iloc[0][factor["feature"]]
            out.explanation = explanation
    return out


def update_call(db: Session, call_id: int, patch: dict, user: AppUser) -> CallOut:
    if db.get(CallRecord, call_id) is None:
        raise HTTPException(404, "Вызов не найден")
    status = patch.get("review_status")
    if status is not None and status not in REVIEW_STATUSES:
        raise HTTPException(422, "Неизвестный статус разбора")
    review = db.get(CallReview, call_id)
    if review is None:
        review = CallReview(call_id=call_id, status_code="pending")
        db.add(review)
    if status:
        review.status_code = status
        # Кто и когда разобрал — фиксирует сервер, а не клиент
        review.reviewed_by = user.email if status != "pending" else None
        review.reviewed_at = datetime.now(timezone.utc) if status != "pending" else None
    if "assigned_to" in patch:
        review.assigned_to = patch["assigned_to"] or None
    if "review_note" in patch:
        review.review_note = patch["review_note"]
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_call(db, call_id)


def bulk_review(db: Session, ids: list[int], status: str, user: AppUser) -> dict:
    if status not in REVIEW_STATUSES:
        raise HTTPException(422, "Неизвестный статус разбора")
    updated = 0
    for cid in ids:
        if db.get(CallRecord, cid) is None:
            continue
        review = db.get(CallReview, cid) or CallReview(call_id=cid)
        db.add(review)
        review.status_code = status
        review.reviewed_by = user.email if status != "pending" else None
        review.reviewed_at = datetime.now(timezone.utc) if status != "pending" else None
        review.updated_at = datetime.now(timezone.utc)
        updated += 1
    db.commit()
    return {"updated": updated}
