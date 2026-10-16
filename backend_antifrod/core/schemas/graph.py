from pydantic import BaseModel


class ClusterOut(BaseModel):
    id: int
    label: str
    pattern: str
    risk_level: str
    template: str | None = None
    number_count: int = 0
    target_count: int = 0
    overlap_share: float = 0
    numbers: list[str] = []
    regions: list[str] = []


class ClusterListOut(BaseModel):
    items: list[ClusterOut]
    next_cursor: str | None = None
    has_more: bool = False
    offset: int = 0
