from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class FraudScenario(Base):
    __tablename__ = "fraud_scenario"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String)


class FalsePositiveLabel(Base):
    __tablename__ = "false_positive_label"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String)


class PhoneNumberScenario(Base):
    __tablename__ = "phone_number_scenario"
    phone_number_id: Mapped[int] = mapped_column(
        ForeignKey("phone_number.id", ondelete="CASCADE"), primary_key=True
    )
    scenario_id: Mapped[int] = mapped_column(ForeignKey("fraud_scenario.id"), primary_key=True)
    score: Mapped[float] = mapped_column(Numeric(5, 4), default=1, nullable=False)
    evidence: Mapped[str | None] = mapped_column(String)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PhoneNumberFalsePositive(Base):
    __tablename__ = "phone_number_false_positive"
    phone_number_id: Mapped[int] = mapped_column(
        ForeignKey("phone_number.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[int] = mapped_column(ForeignKey("false_positive_label.id"), primary_key=True)
    evidence: Mapped[str | None] = mapped_column(String)
    labeled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())