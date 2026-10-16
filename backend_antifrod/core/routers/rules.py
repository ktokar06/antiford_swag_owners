from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.deps import get_current_user, get_db_dep
from core.models.user import AppUser
from core.schemas.rules import PolicyOut, PolicyUpdateIn, RuleOut, RulesUpsertIn
from etl import pipeline
from services import rules_service

router = APIRouter(tags=["rules"], dependencies=[Depends(get_current_user)])


@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db_dep)):
    return rules_service.list_rules(db)


@router.put("/rules")
def upsert_rules(data: RulesUpsertIn, db: Session = Depends(get_db_dep), _: AppUser = Depends(get_current_user)):
    return rules_service.upsert_rules(db, [i.model_dump() for i in data.items])


@router.get("/policy", response_model=PolicyOut)
def get_policy(db: Session = Depends(get_db_dep)):
    return rules_service.get_policy(db)


@router.put("/policy", response_model=PolicyOut)
def update_policy(data: PolicyUpdateIn, db: Session = Depends(get_db_dep), user: AppUser = Depends(get_current_user)):
    return rules_service.update_policy(db, data.model_dump(exclude_none=True), user)


@router.post("/rescore", status_code=202)
def rescore(_: AppUser = Depends(get_current_user)):
    """Пересчитать признаки, граф, скоринг и статистику по уже загруженным данным (в фоне)."""
    return pipeline.start_background(load=False)
