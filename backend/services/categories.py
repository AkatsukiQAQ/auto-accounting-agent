"""Category CRUD service.

Two non-obvious invariants:
- The `other` slug is undeletable — it's the classifier's fallback bucket.
- A category referenced by any transaction cannot be deleted; frontend must
  bulk-reassign first. Returning 409 (not 500) makes that actionable.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Category, Transaction
from backend.services.errors import (
    CategoryInUseError,
    NotFoundError,
    SystemCategoryError,
    ValidationError,
)

SYSTEM_SLUGS: frozenset[str] = frozenset({"other"})
_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def list_categories(session: Session) -> list[Category]:
    return list(
        session.scalars(
            select(Category).order_by(Category.sort_order, Category.id)
        ).all()
    )


def get_category(session: Session, category_id: str) -> Category:
    cat = session.get(Category, category_id)
    if cat is None:
        raise NotFoundError(f"category {category_id!r} not found")
    return cat


def create_category(
    session: Session,
    *,
    id: str,
    label: str,
    color_bg: str,
    color_dot: str,
    keywords: Iterable[str] | None = None,
    auto_assign: bool = True,
    sort_order: int | None = None,
) -> Category:
    _validate_slug(id)
    _validate_color(color_bg, "colorBg")
    _validate_color(color_dot, "colorDot")
    if session.get(Category, id) is not None:
        raise ValidationError(
            f"category {id!r} already exists",
            meta={"field": "id", "id": id},
        )

    if sort_order is None:
        max_order = session.scalar(select(func.coalesce(func.max(Category.sort_order), 0)))
        sort_order = (max_order or 0) + 10

    cat = Category(
        id=id,
        label=label,
        color_bg=color_bg,
        color_dot=color_dot,
        keywords=list(keywords or []),
        auto_assign=auto_assign,
        sort_order=sort_order,
    )
    session.add(cat)
    session.flush()
    return cat


def update_category(
    session: Session, category_id: str, **updates: Any
) -> Category:
    cat = get_category(session, category_id)

    allowed = {"label", "color_bg", "color_dot", "keywords", "auto_assign", "sort_order"}
    unknown = set(updates) - allowed
    if unknown:
        raise ValidationError(
            f"unknown fields: {sorted(unknown)}",
            meta={"fields": sorted(unknown)},
        )

    if "color_bg" in updates:
        _validate_color(updates["color_bg"], "colorBg")
    if "color_dot" in updates:
        _validate_color(updates["color_dot"], "colorDot")
    if "keywords" in updates:
        updates["keywords"] = list(updates["keywords"] or [])

    for k, v in updates.items():
        setattr(cat, k, v)
    session.flush()
    return cat


def delete_category(session: Session, category_id: str) -> None:
    cat = get_category(session, category_id)

    if cat.id in SYSTEM_SLUGS:
        raise SystemCategoryError(
            f"category {cat.id!r} is a system default and cannot be deleted",
            meta={"id": cat.id},
        )

    txn_count = session.scalar(
        select(func.count(Transaction.id)).where(Transaction.category_id == cat.id)
    ) or 0
    if txn_count > 0:
        raise CategoryInUseError(
            f"category {cat.id!r} is referenced by {txn_count} transaction(s)",
            meta={"id": cat.id, "transactionCount": int(txn_count)},
        )

    session.delete(cat)
    session.flush()


# ──────────────────────────────── validators ────────────────────────────────────


def _validate_slug(slug: str) -> None:
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        raise ValidationError(
            f"category id must be lowercase alphanumeric (start with letter, ≤32 chars), got {slug!r}",
            meta={"field": "id"},
        )


def _validate_color(value: str, field: str) -> None:
    if not isinstance(value, str) or not _HEX_RE.fullmatch(value):
        raise ValidationError(
            f"{field} must be a #RRGGBB hex color, got {value!r}",
            meta={"field": field},
        )
