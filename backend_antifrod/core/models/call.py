from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CdrFile(Base):
    __tablename__ = "cdr_file"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(20), default="directory", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="loaded", nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rows_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_valid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_duplicate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_invalid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CallRecord(Base):
    __tablename__ = "call_record"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cdr_file_id: Mapped[int | None] = mapped_column(ForeignKey("cdr_file.id"))
    row_num: Mapped[int | None] = mapped_column(Integer)
    row_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    type: Mapped[str] = mapped_column(String(2), nullable=False)
    imsi: Mapped[str | None] = mapped_column(String(15))
    caller_number: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    callee_number: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    forward_number: Mapped[str | None] = mapped_column(String(10))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hung_up_first_second: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    direction: Mapped[str | None] = mapped_column(String(20))
    connection_type: Mapped[str | None] = mapped_column(String(20))
    time_bucket: Mapped[str | None] = mapped_column(String(20))
    source_country: Mapped[str | None] = mapped_column(String(2))
    source_operator: Mapped[str | None] = mapped_column(String(10))
    foreign_origin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invalid_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvalidCdrRow(Base):
    __tablename__ = "invalid_cdr_row"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cdr_file_id: Mapped[int | None] = mapped_column(ForeignKey("cdr_file.id"))
    row_num: Mapped[int | None] = mapped_column(Integer)
    raw_line: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40))
    fields_found: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
