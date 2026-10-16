from datetime import datetime
from pydantic import BaseModel

from core.schemas.call import CallOut


class BlocksSummaryOut(BaseModel):
    blocked: int = 0
    blocked_numbers: int = 0
    confirmed: int = 0
    falsePositive: int = 0
    missed: int = 0
    pending: int = 0


class BlocksJournalOut(BaseModel):
    items: list[CallOut]
    next_cursor: str | None = None
    has_more: bool = False
    offset: int = 0


class BlockedNumberOut(BaseModel):
    number: str
    number_ref: int | None = None
    blocked_calls: int
    max_risk_score: int
    first_blocked_at: datetime | None = None
    last_blocked_at: datetime | None = None
    confirmed: int = 0
    false_positive: int = 0
    has_fan_pattern: bool = False


class BlockedNumbersOut(BaseModel):
    items: list[BlockedNumberOut]
    total: int = 0
    next_cursor: str | None = None
    has_more: bool = False
    offset: int = 0
