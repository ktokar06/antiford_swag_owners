from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RuleOut(BaseModel):
    code: str
    label: str
    group: str
    description: str | None = None
    base_points: int
    weight: float
    enabled: bool


class RuleIn(BaseModel):
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=1, max_length=120)
    group: Literal["call", "number", "graph"]
    description: str | None = Field(None, max_length=1000)
    base_points: int = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=10)
    enabled: bool


class RulesUpsertIn(BaseModel):
    items: list[RuleIn] = Field(min_length=1, max_length=100)


class PolicyOut(BaseModel):
    name: str
    review_threshold: int
    auto_block_threshold: int
    auto_block_enabled: bool
    false_block_cost: int
    missed_fraud_cost: int
    updated_by: str | None = None


class PolicyUpdateIn(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    review_threshold: int | None = Field(None, ge=0, le=100)
    auto_block_threshold: int | None = Field(None, ge=1, le=100)
    auto_block_enabled: bool | None = None
    false_block_cost: int | None = Field(None, ge=0)
    missed_fraud_cost: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _thresholds(self):
        if (self.review_threshold is not None and self.auto_block_threshold is not None
                and self.review_threshold >= self.auto_block_threshold):
            raise ValueError("Порог проверки должен быть ниже порога автоблокировки")
        return self
