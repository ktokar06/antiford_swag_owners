from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.scoring import BlockingPolicy
from core.models.user import AppUser
from core.schemas.rules import PolicyOut, RuleOut
from services.scoring_service import get_active_policy

POLICY_FIELDS = ("name", "review_threshold", "auto_block_threshold", "auto_block_enabled",
                 "false_block_cost", "missed_fraud_cost")


def list_rules(db: Session) -> list[RuleOut]:
    return []


def upsert_rules(db: Session, items: list[dict]) -> dict:
    raise HTTPException(409, "Скоринг выполняет обученная модель. Веса меняются обучением; доступны пороги политики.")


def _policy_out(row: BlockingPolicy) -> PolicyOut:
    return PolicyOut(**{k: getattr(row, k) for k in POLICY_FIELDS}, updated_by=row.updated_by)


def get_policy(db: Session) -> PolicyOut:
    row = get_active_policy(db)
    db.commit()
    return _policy_out(row)


def update_policy(db: Session, patch: dict, user: AppUser) -> PolicyOut:
    row = get_active_policy(db)
    for k in POLICY_FIELDS:
        if patch.get(k) is not None:
            setattr(row, k, patch[k])
    if row.review_threshold >= row.auto_block_threshold:
        db.rollback()
        raise HTTPException(422, "Порог проверки должен быть ниже порога автоблокировки")
    row.updated_by = user.email
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _policy_out(row)
