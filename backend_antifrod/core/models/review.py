from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ReviewStatus(Base):
    __tablename__ = "review_status"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)


class CallReview(Base):
    __tablename__ = "call_review"
    call_id: Mapped[int] = mapped_column(
        ForeignKey("call_record.id", ondelete="CASCADE"), primary_key=True
    )
    status_code: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(200))
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    review_note: Mapped[str | None] = mapped_column(String)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())