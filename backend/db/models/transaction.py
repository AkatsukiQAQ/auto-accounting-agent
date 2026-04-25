from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String, nullable=False)  # "photo" | "manual"
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_ocr_engine: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_llm_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
