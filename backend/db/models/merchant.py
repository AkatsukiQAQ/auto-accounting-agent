from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from backend.db.base import Base

MERCHANT_SOURCES: tuple[str, ...] = ("seed", "user", "learned")
ALIAS_MATCH_TYPES: tuple[str, ...] = ("contains", "exact", "regex")


class Merchant(Base):
    """Brand table. `id` is a human slug ('starbucks'), not a minted id —
    slugs read better in seed data and rule configs."""

    __tablename__ = "merchants"
    __table_args__ = (
        CheckConstraint("source IN ('seed','user','learned')", name="source"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    aliases: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    default_category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MerchantAlias(Base):
    """User overrides — highest-priority normalization rule."""

    __tablename__ = "merchant_aliases"
    __table_args__ = (
        CheckConstraint("match_type IN ('contains','exact','regex')", name="match_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    raw_pattern: Mapped[str] = mapped_column(String, nullable=False)
    match_type: Mapped[str] = mapped_column(String, nullable=False)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    applied_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
