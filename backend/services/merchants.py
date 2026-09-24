"""Merchant + alias CRUD.

Merchant ids are human slugs derived from the canonical name; CJK-only names
that don't slugify fall back to a short random id. Aliases are the user's
highest-priority normalization overrides (see services/normalization).
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Category, Merchant, MerchantAlias
from backend.db.models.merchant import ALIAS_MATCH_TYPES
from backend.services.errors import NotFoundError, ValidationError
from backend.services.ids import new_merchant_alias_id

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def list_merchants(session: Session, *, q: Optional[str] = None) -> list[Merchant]:
    rows = session.scalars(select(Merchant).order_by(Merchant.id)).all()
    if not q:
        return list(rows)
    needle = q.casefold()
    return [
        m
        for m in rows
        if needle in m.canonical_name.casefold()
        or any(needle in str(a).casefold() for a in m.aliases)
    ]


def get_merchant(session: Session, merchant_id: str) -> Merchant:
    merchant = session.get(Merchant, merchant_id)
    if merchant is None:
        raise NotFoundError(f"merchant {merchant_id!r} not found")
    return merchant


def create_merchant(
    session: Session,
    *,
    canonical_name: str,
    aliases: list[str] | None = None,
    default_category_id: str | None = None,
    logo_url: str | None = None,
) -> Merchant:
    if not canonical_name or not canonical_name.strip():
        raise ValidationError("canonicalName must be non-empty", meta={"field": "canonicalName"})
    _ensure_category(session, default_category_id)

    merchant = Merchant(
        id=_unique_slug(session, canonical_name.strip()),
        canonical_name=canonical_name.strip(),
        aliases=list(aliases or []),
        default_category_id=default_category_id,
        logo_url=logo_url,
        source="user",
    )
    session.add(merchant)
    session.flush()
    return merchant


def update_merchant(session: Session, merchant_id: str, **updates: Any) -> Merchant:
    merchant = get_merchant(session, merchant_id)
    allowed = {"canonical_name", "aliases", "default_category_id", "logo_url"}
    unknown = set(updates) - allowed
    if unknown:
        raise ValidationError(
            f"unknown fields: {sorted(unknown)}", meta={"fields": sorted(unknown)}
        )
    if "canonical_name" in updates and (
        updates["canonical_name"] is None or not updates["canonical_name"].strip()
    ):
        raise ValidationError("canonicalName must be non-empty", meta={"field": "canonicalName"})
    if "default_category_id" in updates:
        _ensure_category(session, updates["default_category_id"])
    if "aliases" in updates and updates["aliases"] is None:
        updates["aliases"] = []

    for k, v in updates.items():
        setattr(merchant, k, v)
    session.flush()
    return merchant


# ───────────────────────────── aliases ─────────────────────────────


def list_aliases(session: Session) -> list[MerchantAlias]:
    return list(
        session.scalars(
            select(MerchantAlias).order_by(MerchantAlias.created_at, MerchantAlias.id)
        ).all()
    )


def create_alias(
    session: Session, *, raw_pattern: str, match_type: str, merchant_id: str
) -> MerchantAlias:
    if not raw_pattern:
        raise ValidationError("rawPattern must be non-empty", meta={"field": "rawPattern"})
    if match_type not in ALIAS_MATCH_TYPES:
        raise ValidationError(
            f"matchType must be one of {ALIAS_MATCH_TYPES}, got {match_type!r}",
            meta={"field": "matchType"},
        )
    if match_type == "regex":
        try:
            re.compile(raw_pattern)
        except re.error as exc:
            raise ValidationError(
                f"rawPattern is not a valid regex: {exc}", meta={"field": "rawPattern"}
            ) from exc
    get_merchant(session, merchant_id)

    alias = MerchantAlias(
        id=new_merchant_alias_id(),
        raw_pattern=raw_pattern,
        match_type=match_type,
        merchant_id=merchant_id,
        applied_count=0,
    )
    session.add(alias)
    session.flush()
    return alias


def delete_alias(session: Session, alias_id: str) -> None:
    alias = session.get(MerchantAlias, alias_id)
    if alias is None:
        raise NotFoundError(f"merchant alias {alias_id!r} not found")
    session.delete(alias)
    session.flush()


# ───────────────────────────── internals ─────────────────────────────


def _ensure_category(session: Session, category_id: str | None) -> None:
    if category_id is not None and session.get(Category, category_id) is None:
        raise ValidationError(
            f"category {category_id!r} does not exist",
            meta={"field": "defaultCategoryId", "categoryId": category_id},
        )


def _unique_slug(session: Session, canonical_name: str) -> str:
    base = _SLUG_STRIP.sub("-", canonical_name.casefold()).strip("-")
    if not base:  # CJK-only names don't slugify to ASCII
        base = f"mch-{uuid.uuid4().hex[:8]}"
    slug = base
    n = 2
    while session.get(Merchant, slug) is not None:
        slug = f"{base}-{n}"
        n += 1
    return slug
