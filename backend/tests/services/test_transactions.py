from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from backend.services.errors import NotFoundError, ValidationError
from backend.services.transactions import (
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)

UTC = timezone.utc


def _mk(session: Session, *, when: datetime, merchant: str = "M", category_id: str = "food",
        amount_cents: int = -500, currency: str = "JPY", source: str = "manual",
        note: str | None = None):
    return create_transaction(
        session,
        occurred_at=when,
        merchant=merchant,
        amount_cents=amount_cents,
        currency=currency,
        category_id=category_id,
        source=source,
        note=note,
    )


# ───────────────────────────── create / validation ─────────────────────────────


def test_create_transaction_assigns_prefixed_id(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC))
    assert t.id.startswith("txn_")
    assert t.merchant == "M"
    assert t.created_at is not None


def test_create_rejects_bad_currency(session: Session) -> None:
    with pytest.raises(ValidationError, match="currency"):
        _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), currency="usd")  # lowercase


def test_create_rejects_zero_amount(session: Session) -> None:
    with pytest.raises(ValidationError, match="non-zero"):
        _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), amount_cents=0)


def test_create_rejects_bool_amount(session: Session) -> None:
    # bool is a subclass of int in Python; guard against it.
    with pytest.raises(ValidationError, match="integer"):
        _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), amount_cents=True)  # type: ignore[arg-type]


def test_create_rejects_unknown_source(session: Session) -> None:
    with pytest.raises(ValidationError, match="source"):
        _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), source="api")


def test_create_rejects_missing_category(session: Session) -> None:
    with pytest.raises(ValidationError, match="nonexistent"):
        _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), category_id="nonexistent")


# ───────────────────────────── get / update / delete ───────────────────────────


def test_get_raises_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_transaction(session, "txn_missing")


def test_update_partial_keeps_other_fields(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), merchant="Old", note="n")
    updated = update_transaction(session, t.id, merchant="New")
    assert updated.merchant == "New"
    assert updated.note == "n"


def test_update_rejects_unknown_field(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC))
    with pytest.raises(ValidationError, match="unknown"):
        update_transaction(session, t.id, bogus="x")


def test_update_validates_updated_currency(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC))
    with pytest.raises(ValidationError, match="currency"):
        update_transaction(session, t.id, currency="JP")


def test_update_sets_note_to_null(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), merchant="M")
    t.note = "before"
    session.flush()
    out = update_transaction(session, t.id, note=None)
    assert out.note is None


def test_delete_removes_row(session: Session) -> None:
    t = _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC))
    delete_transaction(session, t.id)
    with pytest.raises(NotFoundError):
        get_transaction(session, t.id)


def test_delete_missing_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        delete_transaction(session, "txn_nope")


# ─────────────────────────────────── list + filters ────────────────────────────


def test_list_sorts_by_occurred_at_desc_then_id_desc(session: Session) -> None:
    t1 = _mk(session, when=datetime(2026, 4, 20, tzinfo=UTC), merchant="a")
    t2 = _mk(session, when=datetime(2026, 4, 22, tzinfo=UTC), merchant="b")
    t3 = _mk(session, when=datetime(2026, 4, 22, tzinfo=UTC), merchant="c")

    page = list_transactions(session)
    ids = [t.id for t in page.items]
    assert ids[0] in (t2.id, t3.id)
    assert ids[-1] == t1.id


def test_list_filters_by_date_range(session: Session) -> None:
    _mk(session, when=datetime(2026, 1, 1, tzinfo=UTC))
    _mk(session, when=datetime(2026, 3, 1, tzinfo=UTC))
    _mk(session, when=datetime(2026, 5, 1, tzinfo=UTC))

    page = list_transactions(
        session,
        start=datetime(2026, 2, 1, tzinfo=UTC),
        end=datetime(2026, 4, 30, tzinfo=UTC),
    )
    assert len(page.items) == 1
    assert page.items[0].occurred_at.month == 3


def test_list_filters_by_categories(session: Session) -> None:
    _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), category_id="food")
    _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), category_id="transport")
    page = list_transactions(session, categories=["transport"])
    assert len(page.items) == 1
    assert page.items[0].category_id == "transport"


def test_list_search_is_case_insensitive_on_merchant(session: Session) -> None:
    _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), merchant="StArBuCkS Shibuya")
    _mk(session, when=datetime(2026, 4, 23, tzinfo=UTC), merchant="Family Mart")
    page = list_transactions(session, search="starbucks")
    assert len(page.items) == 1
    assert "Starbucks" in page.items[0].merchant or "StArBuCkS" in page.items[0].merchant


def test_list_respects_limit(session: Session) -> None:
    base = datetime(2026, 4, 23, tzinfo=UTC)
    for i in range(5):
        _mk(session, when=base - timedelta(hours=i), merchant=f"m{i}")
    page = list_transactions(session, limit=2)
    assert len(page.items) == 2


def test_list_cursor_paginates_strictly_older(session: Session) -> None:
    base = datetime(2026, 4, 23, tzinfo=UTC)
    made = [_mk(session, when=base - timedelta(hours=i), merchant=f"m{i}") for i in range(5)]
    made_ids_desc = [t.id for t in sorted(made, key=lambda t: (t.occurred_at, t.id), reverse=True)]

    first = list_transactions(session, limit=2)
    assert [t.id for t in first.items] == made_ids_desc[:2]
    assert first.next_cursor is not None

    second = list_transactions(session, limit=2, cursor=first.next_cursor)
    assert [t.id for t in second.items] == made_ids_desc[2:4]

    third = list_transactions(session, limit=2, cursor=second.next_cursor)
    assert [t.id for t in third.items] == made_ids_desc[4:]
    assert third.next_cursor is None


def test_list_rejects_invalid_cursor(session: Session) -> None:
    with pytest.raises(ValidationError, match="cursor"):
        list_transactions(session, cursor="not-base64!")


def test_list_caps_limit_at_200(session: Session) -> None:
    page = list_transactions(session, limit=10_000)
    assert len(page.items) <= 200
