from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

ACCOUNT_KINDS: tuple[str, ...] = (
    "checking",
    "savings",
    "credit",
    "cash",
    "investment",
    "other",
)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('checking','savings','credit','cash','investment','other')",
            name="kind",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # one of ACCOUNT_KINDS
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Materialized: bumped by the ledger cascade on every mutation, never
    # computed on read. `opening_balance_cents` is the reconstruction anchor —
    # balance = opening + SUM(transactions.amount_cents) for this account.
    balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opening_balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    institution: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
