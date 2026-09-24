"""Account service — CRUD, reconciliation, and full-balance recompute.

`balance_cents` is materialized (bumped by `ledger.apply` on every mutation).
`recompute_balance` is the drift-repair tool: it rebuilds the balance from
`opening_balance_cents + SUM(amount_cents)` and is exposed as an ops endpoint
plus used by the Phase-2 integration smoke test.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import Account, Transaction
from backend.db.models.account import ACCOUNT_KINDS
from backend.db.seeders.accounts import DEFAULT_CASH_ACCOUNT_ID
from backend.services import transactions as txn_rows
from backend.services.errors import (
    AccountInUseError,
    NotFoundError,
    SystemAccountError,
    ValidationError,
)
from backend.services.ids import new_account_id
from backend.services.ledger import apply

_SORT_STEP = 10


def list_accounts(session: Session) -> list[Account]:
    return list(
        session.scalars(select(Account).order_by(Account.sort_order, Account.id)).all()
    )


def get_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise NotFoundError(f"account {account_id!r} not found")
    return account


def create_account(
    session: Session,
    *,
    name: str,
    kind: str,
    currency: str,
    opening_balance_cents: int = 0,
    institution: str | None = None,
    color: str | None = None,
    sort_order: int | None = None,
) -> Account:
    _validate_kind(kind)
    _validate_currency(currency)
    _validate_cents(opening_balance_cents, "openingBalanceCents")
    if not name or not name.strip():
        raise ValidationError("name must be non-empty", meta={"field": "name"})

    if sort_order is None:
        current_max = session.scalar(select(func.max(Account.sort_order)))
        sort_order = (current_max or 0) + _SORT_STEP

    account = Account(
        id=new_account_id(),
        name=name.strip(),
        kind=kind,
        currency=currency,
        balance_cents=opening_balance_cents,
        opening_balance_cents=opening_balance_cents,
        institution=institution,
        color=color,
        archived=False,
        sort_order=sort_order,
    )
    session.add(account)
    session.flush()
    return account


def update_account(session: Session, account_id: str, **updates: Any) -> Account:
    account = get_account(session, account_id)

    allowed = {
        "name",
        "kind",
        "currency",
        "opening_balance_cents",
        "institution",
        "color",
        "archived",
        "sort_order",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValidationError(
            f"unknown fields: {sorted(unknown)}", meta={"fields": sorted(unknown)}
        )

    if "kind" in updates:
        _validate_kind(updates["kind"])
    if "name" in updates and (updates["name"] is None or not updates["name"].strip()):
        raise ValidationError("name must be non-empty", meta={"field": "name"})
    if "currency" in updates:
        _validate_currency(updates["currency"])
        if updates["currency"] != account.currency and _transaction_count(session, account_id):
            raise ValidationError(
                "cannot change currency of an account with transactions",
                meta={"field": "currency", "accountId": account_id},
            )
    if "opening_balance_cents" in updates:
        _validate_cents(updates["opening_balance_cents"], "openingBalanceCents")

    for k, v in updates.items():
        setattr(account, k, v)

    # Cascade rule (PHASE_2.md): editing the opening balance rebuilds the
    # materialized balance from scratch — never diffed.
    if "opening_balance_cents" in updates:
        recompute_balance(session, account_id)

    session.flush()
    return account


def delete_account(session: Session, account_id: str) -> None:
    account = get_account(session, account_id)
    if account_id == DEFAULT_CASH_ACCOUNT_ID:
        raise SystemAccountError(
            "the default Cash account backs account-less writes and cannot be deleted",
            meta={"id": account_id},
        )
    count = _transaction_count(session, account_id)
    if count:
        raise AccountInUseError(
            f"account {account_id!r} has {count} transaction(s); reassign them first",
            meta={"id": account_id, "transactionCount": count},
        )
    session.delete(account)
    session.flush()


def reconcile(
    session: Session, account_id: str, *, actual_balance_cents: int
) -> tuple[Account, Transaction | None]:
    """Write a synthetic adjustment so the materialized balance matches reality.

    Zero delta short-circuits without creating a row (`amount_cents=0` is
    rejected by the row engine anyway). The adjustment is a plain `normal` /
    `manual` row so Phase-1 clients can render it.
    """
    account = get_account(session, account_id)
    _validate_cents(actual_balance_cents, "actualBalanceCents")
    delta = actual_balance_cents - account.balance_cents
    if delta == 0:
        return account, None

    adjustment = apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        occurred_at=datetime.now(timezone.utc),
        merchant="Balance adjustment",
        amount_cents=delta,
        currency=account.currency,
        category_id="other",
        source="manual",
        account_id=account_id,
        note="Reconciliation adjustment",
    )
    return account, adjustment


def recompute_balance(session: Session, account_id: str) -> Account:
    """Rebuild `balance_cents` from opening balance + SUM of this account's rows."""
    account = get_account(session, account_id)
    total = session.scalar(
        select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
            Transaction.account_id == account_id
        )
    )
    account.balance_cents = account.opening_balance_cents + int(total or 0)
    session.flush()
    return account


def _transaction_count(session: Session, account_id: str) -> int:
    return int(
        session.scalar(
            select(func.count(Transaction.id)).where(Transaction.account_id == account_id)
        )
        or 0
    )


def _validate_kind(kind: str) -> None:
    if kind not in ACCOUNT_KINDS:
        raise ValidationError(
            f"kind must be one of {ACCOUNT_KINDS}, got {kind!r}", meta={"field": "kind"}
        )


def _validate_currency(currency: str) -> None:
    txn_rows._validate_currency(currency)


def _validate_cents(value: int, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError(f"{field} must be an integer", meta={"field": field})
