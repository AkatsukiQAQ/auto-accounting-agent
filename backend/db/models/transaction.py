from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

TRANSACTION_TYPES: tuple[str, ...] = ("normal", "transfer_out", "transfer_in", "recurring")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('normal','transfer_out','transfer_in','recurring')",
            name="type",
        ),
    )

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
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    # "normal" | "transfer_out" | "transfer_in" | "recurring". System-assigned:
    # never PATCHable; transfer legs are only minted by the transfer service.
    type: Mapped[str] = mapped_column(String, nullable=False, default="normal", server_default="normal")
    transfer_group_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    recurring_rule_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # merchant_raw = verbatim OCR / user input; merchant_normalized = brand-level
    # name. From Phase 2 on, `merchant` is a compat alias kept equal to the
    # normalized value (dropped in a future migration).
    merchant_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merchant_normalized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)  # "photo" | "manual"
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_ocr_engine: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_llm_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
