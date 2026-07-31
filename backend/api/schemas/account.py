from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.api.schemas.base import CamelModel
from backend.api.schemas.transaction import TransactionOut


class AccountOut(CamelModel):
    id: str
    name: str
    # Plain str (not Literal): response validation must never 500 over a value
    # the DB accepted. `kind` membership is enforced in the service layer.
    kind: str
    currency: str
    balance_cents: int
    opening_balance_cents: int
    institution: Optional[str] = None
    color: Optional[str] = None
    archived: bool
    sort_order: int
    created_at: datetime


class AccountCreate(CamelModel):
    name: str
    kind: str
    currency: str
    opening_balance_cents: int = 0
    institution: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class AccountUpdate(CamelModel):
    """Partial update. All fields optional; unset keys preserve DB values."""

    name: Optional[str] = None
    kind: Optional[str] = None
    currency: Optional[str] = None
    opening_balance_cents: Optional[int] = None
    institution: Optional[str] = None
    color: Optional[str] = None
    archived: Optional[bool] = None
    sort_order: Optional[int] = None


class ReconcileIn(CamelModel):
    actual_balance_cents: int


class ReconcileOut(CamelModel):
    account: AccountOut
    # None when the balance already matched and no adjustment row was needed.
    adjustment: Optional[TransactionOut] = None
