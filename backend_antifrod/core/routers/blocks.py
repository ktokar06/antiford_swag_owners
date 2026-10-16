from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.schemas.blocks import BlockedNumbersOut, BlocksJournalOut, BlocksSummaryOut
from services import blocks_service

router = APIRouter(prefix="/blocks", tags=["blocks"], dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=BlocksSummaryOut)
def summary(db: Session = Depends(get_db_dep)):
    return blocks_service.summary(db)


@router.get("/numbers", response_model=BlockedNumbersOut)
def blocked_numbers(
        search: str | None = Query(None, max_length=40),
        sort: str = "-blocked_calls",
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return blocks_service.blocked_numbers(db, {"search": search, "sort": sort, "limit": limit,
                                               "offset": offset, "cursor": cursor})


@router.get("", response_model=BlocksJournalOut)
def journal(
        search: str | None = Query(None, max_length=40),
        review_status: str | None = None,
        sort: str = "-started_at",
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return blocks_service.journal(db, {"search": search, "review_status": review_status, "sort": sort,
                                       "limit": limit, "offset": offset, "cursor": cursor})
