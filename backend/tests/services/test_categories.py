from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from backend.services.categories import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)
from backend.services.errors import (
    CategoryInUseError,
    NotFoundError,
    SystemCategoryError,
    ValidationError,
)
from backend.services.transactions import create_transaction

UTC = timezone.utc


def test_list_returns_seeded_nine_in_sort_order(session: Session) -> None:
    cats = list_categories(session)
    assert [c.id for c in cats] == [
        "food", "transport", "shopping", "bills",
        "entertain", "health", "income", "rent", "other",
    ]


def test_get_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_category(session, "nope")


def test_create_happy_path_auto_sort_order(session: Session) -> None:
    cat = create_category(
        session, id="coffee", label="Coffee",
        color_bg="#AABBCC", color_dot="#112233",
        keywords=["starbucks", "bluebottle"],
    )
    assert cat.id == "coffee"
    # auto sort_order > existing max (90 for "other")
    assert cat.sort_order > 90
    assert cat.keywords == ["starbucks", "bluebottle"]


def test_create_rejects_bad_slug(session: Session) -> None:
    with pytest.raises(ValidationError, match="id"):
        create_category(session, id="Invalid Slug!", label="x",
                        color_bg="#000000", color_dot="#FFFFFF")


def test_create_rejects_bad_color(session: Session) -> None:
    with pytest.raises(ValidationError, match="colorBg"):
        create_category(session, id="x", label="X",
                        color_bg="red", color_dot="#FFFFFF")


def test_create_rejects_duplicate_id(session: Session) -> None:
    with pytest.raises(ValidationError, match="already exists"):
        create_category(session, id="food", label="F",
                        color_bg="#000000", color_dot="#FFFFFF")


def test_update_partial_fields(session: Session) -> None:
    cat = update_category(session, "food", label="Groceries")
    assert cat.label == "Groceries"
    assert cat.keywords  # still intact


def test_update_rejects_unknown_field(session: Session) -> None:
    with pytest.raises(ValidationError, match="unknown"):
        update_category(session, "food", bogus="x")


def test_update_rejects_bad_color(session: Session) -> None:
    with pytest.raises(ValidationError, match="colorDot"):
        update_category(session, "food", color_dot="not-hex")


def test_delete_system_category_raises(session: Session) -> None:
    with pytest.raises(SystemCategoryError):
        delete_category(session, "other")


def test_delete_in_use_category_raises_with_count(session: Session) -> None:
    create_transaction(
        session,
        occurred_at=datetime(2026, 4, 23, tzinfo=UTC),
        merchant="Starbucks",
        amount_cents=-400,
        currency="JPY",
        category_id="food",
        source="manual",
    )
    with pytest.raises(CategoryInUseError) as exc:
        delete_category(session, "food")
    assert exc.value.meta["transactionCount"] == 1


def test_delete_unused_category_succeeds(session: Session) -> None:
    delete_category(session, "bills")
    with pytest.raises(NotFoundError):
        get_category(session, "bills")
