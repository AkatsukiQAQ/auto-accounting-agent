"""ApplyTransactionService — the cascade contract from BACKEND_PHASE_2.md.

Every transaction mutation flows through create/update/delete here so the
materialized `accounts.balance_cents` can never drift from its rows. The
design doc's step "6. Commit" is superseded by this repo's convention:
services only `flush()`; the route (or worker entry point) owns the commit,
so a mid-request failure rolls the row AND its balance bump back together.

Balance bumps go through ORM instances (`account.balance_cents += delta`),
never core UPDATE statements — the session runs `expire_on_commit=False`, so
a bulk UPDATE would leave stale attributes on any Account already loaded in
the identity map.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Account, Transaction
from backend.services import transactions as txn_rows
from backend.services.errors import (
    TransferEndpointRequiredError,
    TransferLegEditError,
    ValidationError,
)

TRANSFER_TYPES: tuple[str, ...] = ("transfer_out", "transfer_in")


def create(
    session: Session,
    *,
    system: bool = False,
    skip_duplicate_check: bool = False,
    **fields: Any,
) -> Transaction:
    """Insert a transaction and bump its account balance atomically.

    `system=True` marks calls from other services (transfer legs, recurring
    worker, reconcile) and unlocks the non-"normal" types; the public API
    surface always calls with the default and is limited to `type="normal"`.
    `skip_duplicate_check` is plumbed through for those callers as well —
    the duplicate detector itself lands with the review queue (Phase-2 M5);
    until then `_duplicate_check` is an inert seam.
    """
    type_ = fields.get("type", "normal")
    if not system:
        if type_ in TRANSFER_TYPES:
            raise TransferEndpointRequiredError(
                "transfer legs are created via POST /api/transfers",
                meta={"field": "type", "type": type_},
            )
        if type_ == "recurring":
            raise ValidationError(
                "recurring rows are created by the recurring worker",
                meta={"field": "type", "type": type_},
            )

    if not skip_duplicate_check:
        _duplicate_check(session, fields)

    row = txn_rows.create_transaction(session, **fields)
    account = session.get(Account, row.account_id)
    assert account is not None  # create_transaction validated existence
    account.balance_cents += row.amount_cents
    session.flush()
    return row


def update(session: Session, transaction_id: str, **patch: Any) -> Transaction:
    """Partial update with balance reconciliation.

    The old and new `(account_id, amount_cents)` pairs are diffed as one unit —
    reversing the old effect and applying the new one covers every combination
    (amount changed, account changed, or both) without case-splitting.
    """
    existing = txn_rows.get_transaction(session, transaction_id)
    if existing.type in TRANSFER_TYPES:
        raise TransferLegEditError(
            "transfer legs are edited as a pair via the transfers endpoints",
            meta={"id": transaction_id, "transferGroupId": existing.transfer_group_id},
        )

    old_account_id = existing.account_id
    old_amount = existing.amount_cents

    row = txn_rows.update_transaction(session, transaction_id, **patch)

    if (old_account_id, old_amount) != (row.account_id, row.amount_cents):
        old_account = session.get(Account, old_account_id)
        new_account = session.get(Account, row.account_id)
        assert old_account is not None and new_account is not None
        old_account.balance_cents -= old_amount
        new_account.balance_cents += row.amount_cents
        session.flush()
    return row


def delete(session: Session, transaction_id: str) -> None:
    """Delete a transaction, reversing its balance effect.

    Deleting either leg of a transfer removes BOTH legs (they are one logical
    event); leaving a dangling half-transfer would corrupt net worth.
    """
    row = txn_rows.get_transaction(session, transaction_id)

    legs: list[Transaction] = [row]
    if row.type in TRANSFER_TYPES and row.transfer_group_id is not None:
        legs = list(
            session.scalars(
                select(Transaction).where(
                    Transaction.transfer_group_id == row.transfer_group_id
                )
            ).all()
        )

    for leg in legs:
        account = session.get(Account, leg.account_id)
        assert account is not None
        account.balance_cents -= leg.amount_cents
        session.delete(leg)
    session.flush()


def _duplicate_check(session: Session, fields: dict[str, Any]) -> None:
    """Inert seam: suspect-duplicate detection (48h window on
    merchant_normalized + amount + account) activates in Phase-2 M5 together
    with the review queue it routes to."""
    return None
