"""Transfer service — a transfer is TWO transaction rows sharing a
`transfer_group_id` (out leg negative on the source account, in leg positive
on the destination), both in the system `transfer` category and excluded from
every spend total via `type`.

Creation goes through `apply.create(system=True, skip_duplicate_check=True)`
so balances stay consistent; legs are never touchable via the generic
transactions surface (apply rejects PATCH on a leg, and generic DELETE of one
leg cascades to both).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Transaction
from backend.services.errors import NotFoundError, ValidationError
from backend.services.ids import new_transfer_group_id
from backend.services.ledger import accounts as account_svc, apply

TRANSFER_CATEGORY_ID = "transfer"


@dataclass(frozen=True)
class TransferPair:
    out_transaction: Transaction
    in_transaction: Transaction
    transfer_group_id: str


def create_transfer(
    session: Session,
    *,
    from_account_id: str,
    to_account_id: str,
    amount_cents: int,
    occurred_at: datetime,
    note: str | None = None,
) -> TransferPair:
    if from_account_id == to_account_id:
        raise ValidationError(
            "cannot transfer within the same account",
            meta={"field": "toAccountId"},
        )
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool) or amount_cents == 0:
        raise ValidationError(
            "amountCents must be a non-zero integer", meta={"field": "amountCents"}
        )

    from_account = account_svc.get_account(session, from_account_id)
    to_account = account_svc.get_account(session, to_account_id)
    if from_account.currency != to_account.currency:
        # Phase 2 scope decision: accounts are single-currency and cross-currency
        # transfers need an FX rate we don't model yet.
        raise ValidationError(
            "cross-currency transfers are not supported "
            f"({from_account.currency} -> {to_account.currency})",
            meta={
                "field": "toAccountId",
                "fromCurrency": from_account.currency,
                "toCurrency": to_account.currency,
            },
        )

    group_id = new_transfer_group_id()
    amount = abs(amount_cents)

    out_row = apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        occurred_at=occurred_at,
        merchant=f"Transfer to {to_account.name}",
        amount_cents=-amount,
        currency=from_account.currency,
        category_id=TRANSFER_CATEGORY_ID,
        source="manual",
        account_id=from_account_id,
        type="transfer_out",
        transfer_group_id=group_id,
        note=note,
    )
    in_row = apply.create(
        session,
        system=True,
        skip_duplicate_check=True,
        occurred_at=occurred_at,
        merchant=f"Transfer from {from_account.name}",
        amount_cents=amount,
        currency=to_account.currency,
        category_id=TRANSFER_CATEGORY_ID,
        source="manual",
        account_id=to_account_id,
        type="transfer_in",
        transfer_group_id=group_id,
        note=note,
    )
    return TransferPair(out_row, in_row, group_id)


def delete_transfer(session: Session, transfer_group_id: str) -> None:
    """Delete both legs of a transfer atomically (balances reversed by apply)."""
    leg = session.scalars(
        select(Transaction).where(Transaction.transfer_group_id == transfer_group_id).limit(1)
    ).first()
    if leg is None:
        raise NotFoundError(f"transfer {transfer_group_id!r} not found")
    apply.delete(session, leg.id)
