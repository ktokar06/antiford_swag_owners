from datetime import datetime
from pydantic import BaseModel, Field


class FactorOut(BaseModel):
    code: str
    label: str
    group: str
    detail: str | None = None
    base_points: int
    weight: float
    enabled: bool
    points: int


class CallOut(BaseModel):
    id: int
    caller: str
    callee: str
    forward: str | None = None
    type: str | None = None
    imsi: str | None = None
    cdr_file_id: int | None = None
    started_at: datetime
    duration_sec: int
    direction: str | None = None
    connection_type: str | None = None
    time_bucket: str | None = None
    source_country: str | None = None
    source_operator: str | None = None
    foreign_origin: bool = False
    hung_up_first_second: bool = False
    is_valid: bool = True
    invalid_reason: str | None = None
    number_ref: int | None = None
    number_label: str | None = None
    counterpart: str | None = None
    risk_score: int = 0
    decision: str = "allow"
    review_status: str = "pending"
    assigned_to: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    risk_factors: list[FactorOut] = []
    probability: float | None = None
    model_version: str | None = None
    explanation: dict | None = None


class CallListOut(BaseModel):
    items: list[CallOut]
    next_cursor: str | None = None
    has_more: bool = False
    offset: int = 0


class CallUpdateIn(BaseModel):
    review_status: str | None = None
    assigned_to: str | None = Field(None, max_length=200)
    review_note: str | None = Field(None, max_length=4000)


class BulkReviewIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)
    review_status: str


class CallAggregateByDayRow(BaseModel):
    day: str
    count: int
    blocked: int = 0
    review: int = 0
    allow: int = 0


class CallAggregateByDayOut(BaseModel):
    rows: list[CallAggregateByDayRow]
