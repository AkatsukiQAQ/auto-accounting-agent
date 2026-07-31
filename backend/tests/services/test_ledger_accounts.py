from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from backend.services.errors import (
    AccountInUseError,
    NotFoundError,
    SystemAccountError,
    ValidationError,
)
from backend.services.ledger import DEFAULT_CASH_ACCOUNT_ID, accounts as account_svc, apply

WHEN = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _spend(session: Session, account_id: str, cents: int = -500) -> None:
    apply.create(
        session,
        occurred_at=WHEN,
        merchant="Lawson",
        amount_cents=cents,
        currency="JPY",
        category_id="food",
        source="manual",
        account_id=account_id,
    )


def test_create_account_mints_id_and_starts_at_opening_balance(session: Session) -> None:
    boa = account_svc.create_account(
        session, name="BoA", kind="checking", currency="USD", opening_balance_cents=12_345
    )
    assert boa.id.startswith("acc_")
    assert boa.balance_cents == 12_345
    assert boa.archived is False


def test_create_account_invalid_kind_rejected(session: Session) -> None:
    with pytest.raises(ValidationError, match="kind"):
        account_svc.create_account(session, name="X", kind="crypto", currency="USD")


def test_list_accounts_ordered_and_includes_default_cash(session: Session) -> None:
    account_svc.create_account(session, name="BoA", kind="checking", currency="USD")
    ids = [a.id for a in account_svc.list_accounts(session)]
    assert ids[0] == DEFAULT_CASH_ACCOUNT_ID  # sort_order 0
    assert len(ids) == 2


def test_get_account_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        account_svc.get_account(session, "acc_missing")


def test_update_currency_blocked_when_transactions_exist(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="USD")
    _spend(session, boa.id)
    with pytest.raises(ValidationError, match="currency"):
        account_svc.update_account(session, boa.id, currency="EUR")
    # Without transactions it's allowed.
    empty = account_svc.create_account(session, name="N26", kind="checking", currency="EUR")
    account_svc.update_account(session, empty.id, currency="USD")
    assert empty.currency == "USD"


def test_update_opening_balance_recomputes_from_scratch(session: Session) -> None:
    boa = account_svc.create_account(
        session, name="BoA", kind="checking", currency="JPY", opening_balance_cents=1_000
    )
    _spend(session, boa.id, cents=-300)
    assert boa.balance_cents == 700

    account_svc.update_account(session, boa.id, opening_balance_cents=5_000)
    assert boa.balance_cents == 4_700


def test_delete_account_with_transactions_conflicts(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    _spend(session, boa.id)
    with pytest.raises(AccountInUseError) as exc:
        account_svc.delete_account(session, boa.id)
    assert exc.value.meta["transactionCount"] == 1


def test_delete_default_cash_account_forbidden(session: Session) -> None:
    with pytest.raises(SystemAccountError):
        account_svc.delete_account(session, DEFAULT_CASH_ACCOUNT_ID)


def test_delete_empty_account_succeeds(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    account_svc.delete_account(session, boa.id)
    with pytest.raises(NotFoundError):
        account_svc.get_account(session, boa.id)


def test_reconcile_writes_adjustment_and_matches_actual(session: Session) -> None:
    boa = account_svc.create_account(session, name="BoA", kind="checking", currency="JPY")
    _spend(session, boa.id, cents=-1_000)

    account, adjustment = account_svc.reconcile(session, boa.id, actual_balance_cents=-700)
    assert account.balance_cents == -700
    assert adjustment is not None
    assert adjustment.amount_cents == 300
    assert adjustment.type == "normal"
    assert adjustment.source == "manual"
    assert adjustment.merchant == "Balance adjustment"


def test_reconcile_zero_delta_is_a_noop(session: Session) -> None:
    boa = account_svc.create_account(
        session, name="BoA", kind="checking", currency="JPY", opening_balance_cents=500
    )
    account, adjustment = account_svc.reconcile(session, boa.id, actual_balance_cents=500)
    assert adjustment is None
    assert account.balance_cents == 500


def test_recompute_balance_repairs_drift(session: Session) -> None:
    boa = account_svc.create_account(
        session, name="BoA", kind="checking", currency="JPY", opening_balance_cents=1_000
    )
    _spend(session, boa.id, cents=-400)
    boa.balance_cents = 999_999  # simulate drift from a hypothetical bug
    session.flush()

    account_svc.recompute_balance(session, boa.id)
    assert boa.balance_cents == 600
