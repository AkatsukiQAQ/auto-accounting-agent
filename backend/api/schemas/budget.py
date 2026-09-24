from datetime import date, datetime
from typing import Literal

from pydantic import ConfigDict, Field, StrictInt

from backend.api.schemas.base import CamelModel

PeriodType = Literal["week", "month"]
Kind = Literal["fixed", "flexible", "discretionary"]


class BudgetInput(CamelModel):
    model_config = ConfigDict(extra="forbid")


class PlanCreate(BudgetInput):
    period_type: PeriodType
    starts_on: date
    ends_on: date | None = None
    currency: str
    planned_income_cents: StrictInt | None = None
    savings_target_cents: StrictInt | None = None
    status: Literal["draft", "active", "closed"] = "active"
    note: str | None = None


class PlanUpdate(BudgetInput):
    planned_income_cents: StrictInt | None = None
    savings_target_cents: StrictInt | None = None
    status: Literal["draft", "active", "closed"] | None = None
    note: str | None = None


class ItemCreate(BudgetInput):
    category_id: str
    limit_cents: StrictInt
    warning_ratio: float = Field(default=0.8, gt=0, le=1)
    kind: Kind = "flexible"
    note: str | None = None


class ItemUpdate(BudgetInput):
    limit_cents: StrictInt | None = None
    warning_ratio: float | None = Field(default=None, gt=0, le=1)
    kind: Kind | None = None
    note: str | None = None


class ItemOut(ItemCreate):
    id: str
    plan_id: str
    created_at: datetime
    updated_at: datetime


class PlanOut(PlanCreate):
    id: str
    ends_on: date
    created_by: str
    created_at: datetime
    updated_at: datetime
    items: list[ItemOut]


class CloneInput(BudgetInput):
    starts_on: date
    ends_on: date | None = None


class QuickInput(BudgetInput):
    amount_cents: StrictInt
    category_id: str
    currency: str
    occurred_on: date
    note: str | None = None


class SetTotalInput(BudgetInput):
    plan_id: str
    category_id: str
    total_cents: StrictInt
    note: str | None = None


class PeriodOut(CamelModel):
    type: PeriodType
    starts_on: date
    ends_on: date
    days_elapsed: int
    days_remaining: int


class ItemSummary(CamelModel):
    category_id: str
    kind: Kind
    limit_cents: int
    spent_cents: int
    remaining_cents: int
    used_ratio: float | None
    pace_ratio: float | None
    status: Literal["safe", "watch", "warning", "over"]


class Unbudgeted(CamelModel):
    category_id: str
    spent_cents: int


class SummaryOut(CamelModel):
    plan_id: str
    currency: str
    timezone: str
    period: PeriodOut
    planned_income_cents: int | None
    savings_target_cents: int | None
    planned_spend_cents: int
    planned_residual_cents: int | None
    actual_spend_cents: int
    remaining_budget_cents: int
    projected_spend_cents: int
    projected_savings_cents: int | None
    safe_daily_spend_cents: int
    items: list[ItemSummary]
    unbudgeted: list[Unbudgeted]
