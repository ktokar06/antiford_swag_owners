from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Float, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ScoringRule(Base):
    __tablename__ = "scoring_rule"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    factor_group: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    base_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BlockingPolicy(Base):
    __tablename__ = "blocking_policy"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    review_threshold: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    auto_block_threshold: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    auto_block_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    false_block_cost: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    missed_fraud_cost: Mapped[int] = mapped_column(Integer, default=12000, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CallRiskFactor(Base):
    __tablename__ = "call_risk_factor"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("call_record.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("scoring_rule.id"))
    detail: Mapped[str | None] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CallDecision(Base):
    __tablename__ = "call_decision"
    call_id: Mapped[int] = mapped_column(
        ForeignKey("call_record.id", ondelete="CASCADE"), primary_key=True
    )
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), default="allow", nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    policy_id: Mapped[int | None] = mapped_column(ForeignKey("blocking_policy.id"))
    probability: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(64))
    feature_values: Mapped[list | None] = mapped_column(JSON, deferred=True)
