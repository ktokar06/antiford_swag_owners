from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.schemas.number import InvalidReasonsOut, NumberListOut, NumberOut, SubscriberAggOut
from services import number_service

router = APIRouter(prefix="/numbers", tags=["numbers"], dependencies=[Depends(get_current_user)])


def number_filters(
        is_valid: bool | None = None,
        has_incoming: bool | None = None,
        has_outgoing: bool | None = None,
        has_forwarded: bool | None = None,
        has_fan_pattern: bool | None = None,
        min_score: int | None = Query(None, ge=0, le=100),
        search_text: str | None = Query(None, max_length=60),
        search_digits: str | None = Query(None, max_length=40),
) -> dict:
    return locals()


@router.get("", response_model=NumberListOut)
def list_numbers(
        f: dict = Depends(number_filters),
        sort: str = "-max_risk_score",
        limit: int = Query(50, ge=1, le=200),
        offset: int | None = Query(None, ge=0),
        cursor: str | None = None,
        db: Session = Depends(get_db_dep),
):
    return number_service.list_numbers(db, {**f, "sort": sort, "limit": limit, "offset": offset, "cursor": cursor})


@router.get("/count")
def count_numbers(f: dict = Depends(number_filters), db: Session = Depends(get_db_dep)) -> int:
    return number_service.count_numbers(db, f)


@router.get("/aggregate/by-subscriber", response_model=SubscriberAggOut)
def aggregate_by_subscriber(db: Session = Depends(get_db_dep)):
    return number_service.aggregate_by_subscriber(db)


@router.get("/aggregate/invalid-reasons", response_model=InvalidReasonsOut)
def aggregate_invalid_reasons(db: Session = Depends(get_db_dep)):
    return number_service.aggregate_invalid_reasons(db)


@router.get("/{number_id}", response_model=NumberOut)
def get_number(number_id: int, db: Session = Depends(get_db_dep)):
    return number_service.get_number(db, number_id)
