from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from core.models.call import CallRecord
from core.models.review import CallReview
from core.models.scoring import CallDecision
from core.schemas.blocks import BlockedNumberOut, BlockedNumbersOut, BlocksJournalOut, BlocksSummaryOut
from core.utils.pagination import digits_only, page, resolve_offset
from services.call_service import build_outs

BLOCKED_NUMBERS_SQL = """
SELECT c.caller_number AS number,
       pn.id AS number_ref,
       count(*) AS blocked_calls,
       max(d.risk_score) AS max_risk_score,
       min(c.started_at) AS first_blocked_at,
       max(c.started_at) AS last_blocked_at,
       count(*) FILTER (WHERE r.status_code = 'confirmed_fraud') AS confirmed,
       count(*) FILTER (WHERE r.status_code = 'false_positive') AS false_positive,
       COALESCE(bool_or(nf.has_fan_pattern), FALSE) AS has_fan_pattern
FROM call_decision d
JOIN call_record c ON c.id = d.call_id
LEFT JOIN call_review r ON r.call_id = d.call_id
LEFT JOIN phone_number pn ON pn.number = c.caller_number
LEFT JOIN number_feature nf ON nf.phone_number_id = pn.id
WHERE d.decision = 'auto_blocked' AND (:search = '' OR c.caller_number LIKE '%' || :search || '%')
GROUP BY c.caller_number, pn.id
ORDER BY {order}, c.caller_number
OFFSET :offset LIMIT :limit
"""

BLOCKED_NUMBERS_COUNT = """
SELECT count(DISTINCT c.caller_number)
FROM call_decision d JOIN call_record c ON c.id = d.call_id
WHERE d.decision = 'auto_blocked' AND (:search = '' OR c.caller_number LIKE '%' || :search || '%')
"""

NUMBER_SORTS = {
    "-blocked_calls": "blocked_calls DESC",
    "-max_risk_score": "max_risk_score DESC, blocked_calls DESC",
    "-last_blocked_at": "last_blocked_at DESC",
}


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def summary(db: Session) -> BlocksSummaryOut:
    blocked_ids = select(CallDecision.call_id).where(CallDecision.decision == "auto_blocked")
    review_count = lambda status: _count(db, select(func.count()).select_from(CallReview)  # noqa: E731
                                         .where(CallReview.status_code == status))
    return BlocksSummaryOut(
        blocked=_count(db, select(func.count()).select_from(CallDecision)
                       .where(CallDecision.decision == "auto_blocked")),
        blocked_numbers=_count(db, text(BLOCKED_NUMBERS_COUNT).bindparams(search="")),
        confirmed=review_count("confirmed_fraud"),
        falsePositive=_count(db, select(func.count()).select_from(CallReview)
                             .where(CallReview.status_code == "false_positive")
                             .where(CallReview.call_id.in_(blocked_ids))),
        missed=_count(db, select(func.count()).select_from(CallReview)
                      .where(CallReview.status_code == "confirmed_fraud")
                      .where(CallReview.call_id.notin_(blocked_ids))),
        pending=_count(db, select(func.count()).select_from(CallReview)
                       .where(CallReview.status_code == "pending")
                       .where(CallReview.call_id.in_(blocked_ids))),
    )


def journal(db: Session, f: dict) -> BlocksJournalOut:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    stmt = (
        select(CallRecord, CallDecision, CallReview)
        .join(CallDecision, CallDecision.call_id == CallRecord.id)
        .join(CallReview, CallReview.call_id == CallRecord.id, isouter=True)
        .where(CallDecision.decision == "auto_blocked")
    )
    digits = digits_only(f.get("search"))
    if digits:
        stmt = stmt.where(or_(CallRecord.caller_number.like(f"%{digits}%"),
                              CallRecord.callee_number.like(f"%{digits}%")))
    if f.get("review_status"):
        stmt = stmt.where(CallReview.status_code == f["review_status"])
    order = CallDecision.risk_score.desc() if f.get("sort") == "-risk_score" else CallRecord.started_at.desc()
    stmt = stmt.order_by(order, CallRecord.id.desc()).offset(offset).limit(limit + 1)
    rows, next_cursor, has_more = page(db.execute(stmt).all(), limit, offset)
    return BlocksJournalOut(items=build_outs(db, rows), next_cursor=next_cursor, has_more=has_more, offset=offset)


def blocked_numbers(db: Session, f: dict) -> BlockedNumbersOut:
    limit = int(f.get("limit") or 50)
    offset = resolve_offset(f.get("cursor"), f.get("offset"))
    search = digits_only(f.get("search"))
    order = NUMBER_SORTS.get(f.get("sort") or "-blocked_calls", NUMBER_SORTS["-blocked_calls"])
    rows = db.execute(text(BLOCKED_NUMBERS_SQL.format(order=order)),
                      {"search": search, "offset": offset, "limit": limit + 1}).mappings().all()
    rows, next_cursor, has_more = page(list(rows), limit, offset)
    total = _count(db, text(BLOCKED_NUMBERS_COUNT).bindparams(search=search))
    return BlockedNumbersOut(
        items=[BlockedNumberOut(**{**r, "number": r["number"].strip()}) for r in rows],
        total=total, next_cursor=next_cursor, has_more=has_more, offset=offset,
    )
