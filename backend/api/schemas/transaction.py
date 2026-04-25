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
    source: Optional[Literal["photo", "manual"]] = None
    confidence: Optional[float] = None
    note: Optional[str] = None
    raw: Optional[RawIn] = None


class TransactionListResponse(CamelModel):
    """List endpoint envelope — carries `nextCursor` alongside `data`."""

    data: list[TransactionOut]
    next_cursor: Optional[str] = None
