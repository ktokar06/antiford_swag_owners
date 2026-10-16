from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from services import stats_api_service as svc

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(db: Session = Depends(get_db_dep)):
    return svc.summary(db)


@router.get("/daily")
def daily(db: Session = Depends(get_db_dep)):
    return {"rows": svc.daily(db)}


@router.get("/hourly")
def hourly(db: Session = Depends(get_db_dep)):
    return {"rows": svc.hourly(db)}


@router.get("/score-distribution")
def score_distribution(db: Session = Depends(get_db_dep)):
    return {"rows": svc.score_distribution(db)}


@router.get("/factors")
def factors(db: Session = Depends(get_db_dep)):
    return {"rows": svc.factors(db)}


@router.get("/directions")
def directions(db: Session = Depends(get_db_dep)):
    return {"rows": svc.directions(db)}


@router.get("/invalid-reasons")
def invalid_reasons(db: Session = Depends(get_db_dep)):
    return {"rows": svc.invalid_reasons(db)}
