from sqlalchemy import Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Country(Base):
    __tablename__ = "country"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    iso_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"), nullable=False)


class Operator(Base):
    __tablename__ = "operator"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("country.id"), nullable=False)


class ConnectionType(Base):
    __tablename__ = "connection_type"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class CallDirection(Base):
    __tablename__ = "call_direction"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class TimeBucket(Base):
    __tablename__ = "time_bucket"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    hour_from: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hour_to: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class NumberKind(Base):
    __tablename__ = "number_kind"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)