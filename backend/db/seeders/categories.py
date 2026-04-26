"""Category seeder — populates the 9 Phase-1 slugs on first boot.

Maps legacy YAML category names (Supermarket / Restaurant / Game / ...) to the
frontend's 9 slugs (food / transport / shopping / bills / entertain / health /
income / rent / other) and attaches color values from the frontend palette
(design/design-references/src/primitives.jsx :: CAT_COLORS).

The mapping is intentionally hardcoded here (not in core/) because color values
are a frontend display concern; core/ stays framework-free.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.categories_seed import load_seed_categories
from backend.db.models import Category


@dataclass(frozen=True)
class _SeedSpec:
    id: str
    label: str
    color_bg: str
    color_dot: str
    legacy_sources: tuple[str, ...] = ()  # legacy YAML `name`s to merge keywords from
    sort_order: int = 0
    extra_keywords: tuple[str, ...] = field(default_factory=tuple)


# Order here becomes sort_order. Mirrors CAT_COLORS declaration in primitives.jsx.
_SPECS: tuple[_SeedSpec, ...] = (
    _SeedSpec(
        id="food",
        label="Food",
        color_bg="#FCE5CE",
        color_dot="#D97706",
        legacy_sources=("Supermarket", "Convenience Store", "Restaurant", "Delivery"),
        sort_order=10,
    ),
    _SeedSpec(
        id="transport",
        label="Transport",
        color_bg="#DCE5F3",
        color_dot="#3B5EAA",
        legacy_sources=("Transportation",),
        sort_order=20,
    ),
    _SeedSpec(
        id="shopping",
        label="Shopping",
        color_bg="#F4DCE8",
        color_dot="#B56576",
        legacy_sources=("Shopping",),
        sort_order=30,
    ),
    _SeedSpec(
        id="bills",
        label="Bills",
        color_bg="#E5E0F3",
        color_dot="#6B5BA8",
        legacy_sources=(),
        sort_order=40,
    ),
    _SeedSpec(
        id="entertain",
        label="Entertain",
        color_bg="#F9E6BD",
        color_dot="#C99A33",
        legacy_sources=("Game", "Sports"),
        sort_order=50,
    ),
    _SeedSpec(
        id="health",
        label="Health",
        color_bg="#DDEED6",
        color_dot="#6E9455",
        legacy_sources=("Health",),
        sort_order=60,
    ),
    _SeedSpec(
        id="income",
        label="Income",
        color_bg="#D7E8CD",
        color_dot="#4F7B49",
        legacy_sources=(),
        sort_order=70,
    ),
    _SeedSpec(
        id="rent",
        label="Rent",
        color_bg="#EEDFC8",
        color_dot="#9E6A37",
        legacy_sources=(),
        sort_order=80,
    ),
    _SeedSpec(
        id="other",
        label="Other",
        color_bg="#E9E4D8",
        color_dot="#8B7E6C",
        legacy_sources=("Others",),
        sort_order=90,
    ),
)


def _merged_keywords(spec: _SeedSpec, legacy_by_name: dict[str, list[str]]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for source in spec.legacy_sources:
        for kw in legacy_by_name.get(source, []):
            if kw not in seen:
                seen.add(kw)
                merged.append(kw)
    for kw in spec.extra_keywords:
        if kw not in seen:
            seen.add(kw)
            merged.append(kw)
    return merged


def _build_rows() -> list[dict[str, object]]:
    legacy = load_seed_categories()
    legacy_by_name: dict[str, list[str]] = {cat.name: list(cat.keywords) for cat in legacy}

    rows: list[dict[str, object]] = []
    for spec in _SPECS:
        rows.append(
            {
                "id": spec.id,
                "label": spec.label,
                "color_bg": spec.color_bg,
                "color_dot": spec.color_dot,
                "keywords": _merged_keywords(spec, legacy_by_name),
                "auto_assign": True,
                "sort_order": spec.sort_order,
            }
        )
    return rows


def seed_categories(session: Session, *, force: bool = False) -> int:
    """Write the 9 default categories if the table is empty.

    Returns the number of rows inserted (0 if already seeded and `force=False`).
    With `force=True`, only missing slugs are added; existing rows are left
    untouched (tests use this to verify idempotency).
    """
    existing_ids: set[str] = set(session.scalars(select(Category.id)).all())

    if existing_ids and not force:
        return 0

    rows = _build_rows()
    inserted = 0
    for row in rows:
        if row["id"] in existing_ids:
            continue
        session.add(Category(**row))
        inserted += 1

    if inserted:
        session.flush()
    return inserted


def iter_seed_specs() -> Iterable[_SeedSpec]:
    """Exposed for tests — yields the frozen seed specs in sort order."""
    return iter(_SPECS)
