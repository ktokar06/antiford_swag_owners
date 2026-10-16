from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Subscriber(Base):
    __tablename__ = "subscriber"
    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="person", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PhoneNumber(Base):
    __tablename__ = "phone_number"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    subscriber_id: Mapped[int | None] = mapped_column(ForeignKey("subscriber.id"))
    region_code: Mapped[str | None] = mapped_column(String(10))
    operator_code: Mapped[str | None] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invalid_reason: Mapped[str | None] = mapped_column(String(120))
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())