from datetime import datetime
from pydantic import BaseModel


class NumberOut(BaseModel):
    id: int
    number: str
    subscriber: str | None = None
    region: str | None = None
    operator: str | None = None
    kind: str = "unknown"
    is_valid: bool = True
    invalid_reason: str | None = None
    has_incoming: bool = False
    has_outgoing: bool = False
    has_forwarded: bool = False
    has_fan_pattern: bool = False
    fan_group: str | None = None
    total_calls: int = 0
    outgoing_calls: int = 0
    calls_per_hour: int = 0
    unique_counterparts: int = 0
    region_reach: int = 0
    short_call_share: float = 0
    unanswered_share: float = 0
    numbers_per_subscriber: int = 1
    max_risk_score: int = 0
    avg_risk_score: float = 0
    window_days: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class NumberListOut(BaseModel):
    items: list[NumberOut]
    next_cursor: str | None = None
    has_more: bool = False
    offset: int = 0


class SubscriberAggRow(BaseModel):
    subscriber: str
    count: int


class SubscriberAggOut(BaseModel):
    rows: list[SubscriberAggRow]


class InvalidReasonRow(BaseModel):
    code: str | None = None
    invalid_reason: str
    count: int


class InvalidReasonsOut(BaseModel):
    rows: list[InvalidReasonRow]
