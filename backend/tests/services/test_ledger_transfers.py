from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Transaction
from backend.services.errors import NotFoundError, ValidationError
from backend.services.ledger import accounts as account_svc, transfers as transfer_svc

WHEN = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _accounts(session: Session) -> tuple:
    a = account_svc.create_account(
        session, name="Checking", kind="checking", currency="JPY", opening_balance_cents=10_000
    )
    b = account_svc.create_account(
        session, name="Savings", kind="savings", currency="JPY", opening_balance_cents=0
    )
    return a, b


def test_create_transfer_two_linked_legs_and_balances(session: Session) -> None:
    a, b = _accounts(session)
    pair = transfer_svc.create_transfer(
        session, from_account_id=a.id, to_account_id=b.id, amount_cents=3_000, occurred_at=WHEN
    )

    assert pair.out_transaction.type == "transfer_out"
    assert pair.out_transaction.amount_cents == -3_000
    assert pair.out_transaction.merchant == "Transfer to Savings"
    assert pair.in_transaction.type == "transfer_in"
    assert pair.in_transaction.amount_cents == 3_000
    assert pair.in_transaction.merchant == "Transfer from Checking"
    assert pair.out_transaction.transfer_group_id == pair.in_transaction.transfer_group_id
    assert pair.out_transaction.category_id == "transfer"

    assert a.balance_cents == 7_000
    assert b.balance_cents == 3_000


def test_create_transfer_negative_amount_normalized(session: Session) -> None:
    a, b = _accounts(session)
    pair = transfer_svc.create_transfer(
        session, from_account_id=a.id, to_account_id=b.id, amount_cents=-3_000, occurred_at=WHEN
    )
    assert pair.out_transaction.amount_cents == -3_000
    assert pair.in_transaction.amount_cents == 3_000


def test_create_transfer_same_account_rejected(session: Session) -> None:
    a, _ = _accounts(session)
    with pytest.raises(ValidationError, match="same account"):
        transfer_svc.create_transfer(
            session, from_account_id=a.id, to_account_id=a.id, amount_cents=100, occurred_at=WHEN
        )


def test_create_transfer_cross_currency_rejected(session: Session) -> None:
    a, _ = _accounts(session)
    usd = account_svc.create_account(session, name="BoA", kind="checking", currency="USD")
    with pytest.raises(ValidationError, match="cross-currency"):
        transfer_svc.create_transfer(
            session, from_account_id=a.id, to_account_id=usd.id, amount_cents=100, occurred_at=WHEN
        )


def test_create_transfer_zero_amount_rejected(session: Session) -> None:
    a, b = _accounts(session)
    with pytest.raises(ValidationError, match="amountCents"):
        transfer_svc.create_transfer(
            session, from_account_id=a.id, to_account_id=b.id, amount_cents=0, occurred_at=WHEN
        )


def test_delete_transfer_removes_both_legs_and_reverses(session: Session) -> None:
    a, b = _accounts(session)
    pair = transfer_svc.create_transfer(
        session, from_account_id=a.id, to_account_id=b.id, amount_cents=3_000, occurred_at=WHEN
    )
    transfer_svc.delete_transfer(session, pair.transfer_group_id)

    assert int(session.scalar(select(func.count(Transaction.id))) or 0) == 0
    assert a.balance_cents == 10_000
    assert b.balance_cents == 0


def test_delete_transfer_unknown_group_404(session: Session) -> None:
    with pytest.raises(NotFoundError):
        transfer_svc.delete_transfer(session, "xfr_missing")
