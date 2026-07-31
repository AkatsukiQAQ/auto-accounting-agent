"""ApplyTransactionService cascade tests — the most important invariants in
Phase 2: every mutation keeps `accounts.balance_cents` consistent, atomically.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Account, Transaction
from backend.services.errors import (
    ArchivedAccountError,
    TransferEndpointRequiredError,
    TransferLegEditError,
    ValidationError,
)
from backend.services.ledger import DEFAULT_CASH_ACCOUNT_ID, accounts as account_svc, apply

WHEN = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _fields(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "occurred_at": WHEN,
        "merchant": "Lawson",
        "amount_cents": -500,
        "currency": "JPY",
        "category_id": "food",
        "source": "manual",
    }
    base.update(overrides)
    return base


def _cash(session: Session) -> Account:
    account = session.get(Account, DEFAULT_CASH_ACCOUNT_ID)
    assert account is not None
    return account


def _row_count(session: Session) -> int:
    return int(session.scalar(select(func.count(Transaction.id))) or 0)


# ─────────────────────────────── create ───────────────────────────────


def test_create_bumps_account_balance(session: Session) -> None:
    txn = apply.create(session, **_fields())
    assert txn.account_id == DEFAULT_CASH_ACCOUNT_ID
    assert _cash(session).balance_cents == -500


def test_create_without_account_id_lands_on_default_cash(session: Session) -> None:
    txn = apply.create(session, **_fields(account_id=None))
    assert txn.account_id == DEFAULT_CASH_ACCOUNT_ID


def test_create_with_explicit_account(session: Session) -> None:
    boa = account_svc.create_account(
        session, name="BoA", kind="checking", currency="USD", opening_balance_cents=10_000
    )
    apply.create(session, **_fields(account_id=boa.id, currency="USD", amount_cents=-2_000))
    assert boa.balance_cents == 8_000
    assert _cash(session).balance_cents == 0


def test_create_on_archived_account_rejected(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="USD")
    account_svc.update_account(session, boa.id, archived=True)
    with pytest.raises(ArchivedAccountError):
        apply.create(session, **_fields(account_id=boa.id))


def test_create_transfer_type_requires_transfers_endpoint(session: Session) -> None:
    with pytest.raises(TransferEndpointRequiredError):
        apply.create(session, **_fields(type="transfer_out"))


def test_create_recurring_type_reserved_for_worker(session: Session) -> None:
    with pytest.raises(ValidationError, match="recurring"):
        apply.create(session, **_fields(type="recurring"))


def test_create_mid_cascade_failure_leaves_no_partial_state(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Row insert succeeds, balance bump raises → after rollback there must be
    neither a row nor a balance change (the route's commit-or-rollback owns
    atomicity; this asserts nothing is half-flushed inside the cascade)."""
    # Persist the fixture's seed data first — in production it's committed at
    # boot; without this, rollback() below would erase Cash itself.
    session.commit()
    real_get = session.get
    account_gets = {"n": 0}

    def exploding_get(entity, ident, *args, **kwargs):  # type: ignore[no-untyped-def]
        if entity is Account:
            account_gets["n"] += 1
            if account_gets["n"] >= 2:  # 1st get validates; 2nd is the balance bump
                raise RuntimeError("boom mid-cascade")
        return real_get(entity, ident, *args, **kwargs)

    monkeypatch.setattr(session, "get", exploding_get)
    with pytest.raises(RuntimeError, match="boom"):
        apply.create(session, **_fields())
    monkeypatch.undo()

    session.rollback()
    assert _row_count(session) == 0
    assert _cash(session).balance_cents == 0


# ─────────────────────────────── update ───────────────────────────────


def test_update_amount_moves_balance_by_delta(session: Session) -> None:
    txn = apply.create(session, **_fields(amount_cents=-500))
    apply.update(session, txn.id, amount_cents=-800)
    assert _cash(session).balance_cents == -800


def test_update_account_moves_balance_between_accounts(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    txn = apply.create(session, **_fields(amount_cents=-500))
    apply.update(session, txn.id, account_id=boa.id)
    assert _cash(session).balance_cents == 0
    assert boa.balance_cents == -500


def test_update_amount_and_account_together(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    txn = apply.create(session, **_fields(amount_cents=-500))
    apply.update(session, txn.id, account_id=boa.id, amount_cents=-900)
    assert _cash(session).balance_cents == 0
    assert boa.balance_cents == -900


def test_update_category_only_leaves_balances_alone(session: Session) -> None:
    txn = apply.create(session, **_fields())
    apply.update(session, txn.id, category_id="shopping")
    assert _cash(session).balance_cents == -500


def test_update_system_fields_rejected(session: Session) -> None:
    txn = apply.create(session, **_fields())
    with pytest.raises(ValidationError, match="unknown fields"):
        apply.update(session, txn.id, type="recurring")
    with pytest.raises(ValidationError, match="unknown fields"):
        apply.update(session, txn.id, transfer_group_id="xfr_x")


def test_update_transfer_leg_forbidden(session: Session) -> None:
    leg = apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        **_fields(type="transfer_out", transfer_group_id="xfr_test"),
    )
    with pytest.raises(TransferLegEditError):
        apply.update(session, leg.id, amount_cents=-999)


# ─────────────────────────────── delete ───────────────────────────────


def test_delete_reverses_balance(session: Session) -> None:
    txn = apply.create(session, **_fields())
    apply.delete(session, txn.id)
    assert _cash(session).balance_cents == 0
    assert _row_count(session) == 0


def test_delete_transfer_leg_removes_both_legs(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    out_leg = apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        **_fields(type="transfer_out", transfer_group_id="xfr_pair", amount_cents=-1_000),
    )
    apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        **_fields(
            type="transfer_in",
            transfer_group_id="xfr_pair",
            account_id=boa.id,
            amount_cents=1_000,
            merchant="Transfer from Cash",
        ),
    )
    assert _cash(session).balance_cents == -1_000
    assert boa.balance_cents == 1_000

    apply.delete(session, out_leg.id)

    assert _row_count(session) == 0
    assert _cash(session).balance_cents == 0
    assert boa.balance_cents == 0
