"""Default-account seeder.

The ledger requires every transaction to carry an `account_id`. Rows written
by clients that predate accounts (frontend Phase 1) fall back to this default
Cash account, so it must exist in every database — Alembic-migrated ones get
it from `0003_transactions_extend`; `create_all` databases (tests, fresh dev)
get it here at boot.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Account
from backend.services.settings import get_settings

DEFAULT_CASH_ACCOUNT_ID = "acc_cash_default"


def ensure_default_cash_account(session: Session) -> bool:
    """Insert the default Cash account if missing. Returns True when inserted.

    Currency follows the profile's defaultCurrency at creation time; existing
    rows are never touched (idempotent).
    """
    if session.get(Account, DEFAULT_CASH_ACCOUNT_ID) is not None:
        return False
    currency = get_settings(session)["profile"]["defaultCurrency"]
    session.add(
        Account(
            id=DEFAULT_CASH_ACCOUNT_ID,
            name="Cash",
            kind="cash",
            currency=currency,
            balance_cents=0,
            opening_balance_cents=0,
            archived=False,
            sort_order=0,
        )
    )
    session.flush()
    return True
