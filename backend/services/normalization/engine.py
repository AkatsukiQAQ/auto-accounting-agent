"""NormalizationEngine — aliases → strip → brand → fallback."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Merchant, MerchantAlias
from backend.services.normalization.strippers import strip_location, title_case_if_shouty

MatchedBy = Literal["alias", "strip", "brand", "fallback"]


@dataclass(frozen=True)
class NormalizationOutcome:
    normalized: str
    merchant_id: Optional[str]
    matched_by: MatchedBy


def normalize(
    session: Session, raw: str, *, count_alias_hits: bool = False
) -> NormalizationOutcome:
    """Normalize one raw merchant string.

    `count_alias_hits=False` keeps the call side-effect free — the stateless
    `POST /api/normalize` preview MUST NOT write; the pipeline and the ledger
    pass True so `merchant_aliases.applied_count` tracks rule usage.
    """
    raw = (raw or "").strip()
    if not raw:
        return NormalizationOutcome(normalized="Unknown", merchant_id=None, matched_by="fallback")

    # 1. User aliases — highest priority, matched against the FULL raw string.
    hit = _alias_match(session, raw)
    if hit is not None:
        merchant, alias = hit
        if count_alias_hits:
            alias.applied_count += 1
            session.flush()
        return NormalizationOutcome(
            normalized=merchant.canonical_name, merchant_id=merchant.id, matched_by="alias"
        )

    # 2. Strip location/store suffixes.
    stripped = strip_location(raw)

    # 3. Brand table on the stripped name.
    brand = _brand_lookup(session, stripped)
    if brand is not None:
        return NormalizationOutcome(
            normalized=brand.canonical_name, merchant_id=brand.id, matched_by="brand"
        )

    # 4. Fallback — the stripped name itself.
    normalized = title_case_if_shouty(stripped)
    matched_by: MatchedBy = "strip" if normalized != raw else "fallback"
    return NormalizationOutcome(normalized=normalized, merchant_id=None, matched_by=matched_by)


def _alias_match(session: Session, raw: str) -> tuple[Merchant, MerchantAlias] | None:
    aliases = session.scalars(
        select(MerchantAlias).order_by(MerchantAlias.created_at, MerchantAlias.id)
    ).all()
    needle = raw.casefold()
    for alias in aliases:
        if alias.match_type == "exact":
            matched = needle == alias.raw_pattern.casefold()
        elif alias.match_type == "contains":
            matched = alias.raw_pattern.casefold() in needle
        else:  # regex — validated at creation; guard anyway
            try:
                matched = re.search(alias.raw_pattern, raw) is not None
            except re.error:
                matched = False
        if matched:
            merchant = session.get(Merchant, alias.merchant_id)
            if merchant is not None:
                return merchant, alias
    return None


def _brand_key(name: str) -> str:
    return "".join(name.casefold().split())


def _brand_lookup(session: Session, name: str) -> Merchant | None:
    key = _brand_key(name)
    if not key:
        return None
    for merchant in session.scalars(select(Merchant).order_by(Merchant.id)).all():
        if key == _brand_key(merchant.canonical_name):
            return merchant
        if any(key == _brand_key(str(a)) for a in merchant.aliases):
            return merchant
    return None
