from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from backend.api.schemas.base import CamelModel


class RawIn(CamelModel):
    image_url: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_engine: Optional[str] = None
    llm_model: Optional[str] = None


class RawOut(CamelModel):
    image_url: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_engine: Optional[str] = None
    llm_model: Optional[str] = None


class TransactionOut(CamelModel):
    id: str
    occurred_at: datetime
    created_at: datetime
    merchant: str
    amount_cents: int
    currency: str
    category_id: str
    account_id: str
    # Plain str (not Literal) on purpose: response validation must never 500 a
    # list endpoint over a value the DB accepted.
    type: str
    transfer_group_id: Optional[str] = None
    recurring_rule_id: Optional[str] = None
    merchant_raw: Optional[str] = None
    merchant_normalized: Optional[str] = None
    source: Literal["photo", "manual"]
    confidence: Optional[float] = None
    note: Optional[str] = None
    raw: Optional[RawOut] = None


class TransactionCreate(CamelModel):
    occurred_at: datetime
    merchant: str
    amount_cents: int
    currency: str
    category_id: str
    # Optional for Phase-1 clients — the service falls back to the default
    # Cash account when absent.
    account_id: Optional[str] = None
    # Plain str so `type: "transfer_out"` reaches the ledger service and gets
    # the spec'd 400 `use_transfers_endpoint` instead of a generic 400.
    type: Optional[str] = None
    source: Literal["photo", "manual"]
    confidence: Optional[float] = None
    note: Optional[str] = None
    raw: Optional[RawIn] = None


class TransactionUpdate(CamelModel):
    """Partial update. All fields optional; unset keys preserve DB values."""

    occurred_at: Optional[datetime] = None
    merchant: Optional[str] = None
    amount_cents: Optional[int] = None
    currency: Optional[str] = None
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    source: Optional[Literal["photo", "manual"]] = None
    confidence: Optional[float] = None
    note: Optional[str] = None
    raw: Optional[RawIn] = None


class TransactionListResponse(CamelModel):
    """List endpoint envelope — carries `nextCursor` alongside `data`."""

    data: list[TransactionOut]
    next_cursor: Optional[str] = None
