from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CallFeature(Base):
    __tablename__ = "call_feature"
    call_record_id: Mapped[int] = mapped_column(
        ForeignKey("call_record.id", ondelete="CASCADE"), primary_key=True
    )
    call_count: Mapped[int | None] = mapped_column(Integer)
    call_sum_dur: Mapped[int | None] = mapped_column(BigInteger)
    call_min_dur: Mapped[int | None] = mapped_column(Integer)
    call_max_dur: Mapped[int | None] = mapped_column(Integer)
    call_mean_dur: Mapped[float | None] = mapped_column(Numeric(10, 2))
    call_median_dur: Mapped[float | None] = mapped_column(Numeric(10, 2))
    call_std_dur: Mapped[float | None] = mapped_column(Numeric(10, 2))
    window_5_count: Mapped[int | None] = mapped_column(Integer)
    window_10_count: Mapped[int | None] = mapped_column(Integer)
    window_30_count: Mapped[int | None] = mapped_column(Integer)
    window_60_count: Mapped[int | None] = mapped_column(Integer)
    window_300_count: Mapped[int | None] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NumberFeature(Base):
    __tablename__ = "number_feature"
    phone_number_id: Mapped[int] = mapped_column(
        ForeignKey("phone_number.id", ondelete="CASCADE"), primary_key=True
    )
    window_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    total_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    outgoing_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calls_per_hour: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_counterparts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    region_reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    short_call_share: Mapped[float] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    unanswered_share: Mapped[float] = mapped_column(Numeric(5, 4), default=0, nullable=False)
    has_incoming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_outgoing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_forwarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    numbers_per_subscriber: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_risk_score: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    has_fan_pattern: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fan_group: Mapped[str | None] = mapped_column(String(120))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())