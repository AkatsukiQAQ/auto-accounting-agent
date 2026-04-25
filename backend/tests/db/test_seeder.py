from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Category
from backend.db.seeders.categories import iter_seed_specs, seed_categories

EXPECTED_SLUGS = (
    "food",
    "transport",
    "shopping",
    "bills",
    "entertain",
    "health",
    "income",
    "rent",
    "other",
)


def _all_categories(session: Session) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.sort_order)).all())


def test_seeder_writes_nine_slugs(session: Session) -> None:
    inserted = seed_categories(session)
    assert inserted == 9

    cats = _all_categories(session)
    assert [c.id for c in cats] == list(EXPECTED_SLUGS)


def test_seeder_colors_match_frontend_palette(session: Session) -> None:
    seed_categories(session)
    cats = {c.id: c for c in _all_categories(session)}

    # Spot-check a few against CAT_COLORS in primitives.jsx
    assert cats["food"].color_bg == "#FCE5CE"
    assert cats["food"].color_dot == "#D97706"
    assert cats["transport"].color_dot == "#3B5EAA"
    assert cats["other"].color_bg == "#E9E4D8"

    # Every slug must carry both colors as 7-char hex strings.
    for cat in cats.values():
        assert cat.color_bg.startswith("#") and len(cat.color_bg) == 7
        assert cat.color_dot.startswith("#") and len(cat.color_dot) == 7


def test_seeder_merges_legacy_keywords_into_food(session: Session) -> None:
    seed_categories(session)
    food = session.get(Category, "food")
    assert food is not None
    # Supermarket + Convenience Store + Restaurant + Delivery all merged here.
    assert "セブンイレブン" in food.keywords  # from Convenience Store
    assert "レストラン" in food.keywords  # from Restaurant
    assert "Uber Eats" in food.keywords  # from Delivery


def test_seeder_entertain_merges_game_and_sports(session: Session) -> None:
    seed_categories(session)
    entertain = session.get(Category, "entertain")
    assert entertain is not None
    assert "Steam" in entertain.keywords  # from Game
    assert "スポーツ" in entertain.keywords  # from Sports


def test_seeder_empty_seed_slugs_have_no_keywords(session: Session) -> None:
    """bills / income / rent are new in Phase 1 with no legacy source."""
    seed_categories(session)
    for slug in ("bills", "income", "rent"):
        cat = session.get(Category, slug)
        assert cat is not None, slug
        assert cat.keywords == [], f"{slug} should start empty"


def test_seeder_is_idempotent(session: Session) -> None:
    first = seed_categories(session)
    assert first == 9

    second = seed_categories(session)
    assert second == 0, "re-running seeder on populated DB must be a no-op"

    cats = _all_categories(session)
    assert len(cats) == 9


def test_seeder_force_backfills_missing_only(session: Session) -> None:
    """force=True adds missing slugs without mutating existing rows."""
    # Manually write one row with a different color to prove it's not overwritten.
    session.add(
        Category(
            id="food",
            label="Food",
            color_bg="#000000",
            color_dot="#111111",
            keywords=["custom"],
            auto_assign=False,
            sort_order=999,
        )
    )
    session.flush()

    inserted = seed_categories(session, force=True)
    assert inserted == 8

    food = session.get(Category, "food")
    assert food is not None
    assert food.color_bg == "#000000", "existing row must not be overwritten"
    assert food.auto_assign is False


def test_seed_specs_sort_order_is_strictly_increasing() -> None:
    orders = [spec.sort_order for spec in iter_seed_specs()]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
