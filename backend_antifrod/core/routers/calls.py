from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.models.user import AppUser
from core.schemas.call import BulkReviewIn, CallAggregateByDayOut, CallListOut, CallOut, CallUpdateIn
from services import call_service

router = APIRouter(prefix="/calls", tags=["calls"], dependencies=[Depends(get_current_user)])


def call_filters(
        decision: str | None = None,
        review_status: str | None = None,
        direction: str | None = None,
        is_valid: bool | None = None,
        foreign_origin: bool | None = None,
        search: str | None = Query(None, max_length=40),
        number_ref: int | None = None,
        cdr_file_id: int | None = None,
        type: str | None = Query(None, pattern="^0[123]$"),
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_score: int | None = Query(None, ge=0, le=100),
) -> dict:
    return locals()


@router.get("", response_model=CallListOut)
def list_calls(
        f: dict = Depends(call_filters),
        sort: str = "-risk_score",
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return call_service.list_calls(db, {**f, "sort": sort, "limit": limit, "offset": offset, "cursor": cursor})


@router.get("/count")
def count_calls(f: dict = Depends(call_filters), db: Session = Depends(get_db_dep)) -> int:
    return call_service.count_calls(db, f)


@router.get("/aggregate/by-day", response_model=CallAggregateByDayOut)
def aggregate_by_day(db: Session = Depends(get_db_dep)):
    return call_service.aggregate_by_day(db)


@router.post("/bulk-review")
def bulk_review(data: BulkReviewIn, db: Session = Depends(get_db_dep), user: AppUser = Depends(get_current_user)):
    return call_service.bulk_review(db, data.ids, data.review_status, user)


@router.get("/{call_id}", response_model=CallOut)
def get_call(call_id: int, db: Session = Depends(get_db_dep)):
    return call_service.get_call(db, call_id)


@router.patch("/{call_id}", response_model=CallOut)
def update_call(call_id: int, data: CallUpdateIn, db: Session = Depends(get_db_dep),
                user: AppUser = Depends(get_current_user)):
    return call_service.update_call(db, call_id, data.model_dump(exclude_unset=True), user)
