"""Transaction row engine — validation + CRUD mechanics, NO ledger cascade.

Pure business logic — no HTTP, no Pydantic DTOs, no auth. Inputs and outputs
use snake_case DB column names; camelCase conversion lives in `api/schemas/`.

Phase 2: account balances are materialized, so every mutation must also bump
`accounts.balance_cents`. That cascade lives in `backend/services/ledger/`
(apply.py) — ROUTES AND WORKERS MUST GO THROUGH IT, never call the mutating
functions here directly. Direct calls remain only for the ledger package
itself and for row-level unit tests.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.db.models import Account, Category, Transaction
from backend.db.models.transaction import TRANSACTION_TYPES
from backend.db.seeders.accounts import DEFAULT_CASH_ACCOUNT_ID
from backend.services.errors import ArchivedAccountError, NotFoundError, ValidationError
from backend.services.ids import new_transaction_id

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


@dataclass(frozen=True)
class TransactionPage:
    items: list[Transaction]
    next_cursor: Optional[str]


# ─────────────────────────── create / get / update / delete ───────────────────────────


def create_transaction(
    session: Session,
    *,
    occurred_at: datetime,
    merchant: str | None,
    amount_cents: int,
    currency: str,
    category_id: str,
    source: str,
    granularity: str = "transaction",
    account_id: str | None = None,
    type: str = "normal",
    transfer_group_id: str | None = None,
    recurring_rule_id: str | None = None,
    merchant_raw: str | None = None,
    merchant_normalized: str | None = None,
    confidence: float | None = None,
    note: str | None = None,
    raw_image_url: str | None = None,
    raw_ocr_text: str | None = None,
    raw_ocr_engine: str | None = None,
    raw_llm_model: str | None = None,
) -> Transaction:
    """Insert one row. `account_id=None` falls back to the default Cash account
    (Phase-1 clients don't send one). Does NOT touch account balances — that is
    `services/ledger/apply.py`'s job.
    """
    _validate_currency(currency)
    _validate_amount(amount_cents)
    _validate_source(source)
    if granularity not in ("transaction", "quick", "aggregate_adjustment"):
        raise ValidationError("Invalid granularity")
    _validate_type(type)
    _ensure_category_exists(session, category_id)
    account_id = account_id or DEFAULT_CASH_ACCOUNT_ID
    _ensure_account_writable(session, account_id)

    txn = Transaction(
        id=new_transaction_id(),
        occurred_at=_utc_datetime(occurred_at),
        merchant=merchant,
        amount_cents=amount_cents,
        currency=currency,
        category_id=category_id,
        source=source,
        granularity=granularity,
        account_id=account_id,
        type=type,
        transfer_group_id=transfer_group_id,
        recurring_rule_id=recurring_rule_id,
        merchant_raw=merchant_raw,
        merchant_normalized=merchant_normalized,
        confidence=confidence,
        note=note,
        raw_image_url=raw_image_url,
        raw_ocr_text=raw_ocr_text,
        raw_ocr_engine=raw_ocr_engine,
        raw_llm_model=raw_llm_model,
    )
    session.add(txn)
    session.flush()
    return txn


def get_transaction(session: Session, transaction_id: str) -> Transaction:
    txn = session.get(Transaction, transaction_id)
    if txn is None:
        raise NotFoundError(f"transaction {transaction_id!r} not found")
    return txn


def update_transaction(
    session: Session, transaction_id: str, **updates: Any
) -> Transaction:
    """Apply a partial update. Keys absent from `updates` keep their old values;
    keys present with `None` set the column to NULL (when the column is nullable).
    """
    txn = get_transaction(session, transaction_id)

    # `type`, `transfer_group_id`, `recurring_rule_id` are system-assigned and
    # deliberately absent — they must never be PATCHable.
    allowed = {
        "occurred_at",
        "merchant",
        "amount_cents",
        "currency",
        "category_id",
        "source",
        "account_id",
        "merchant_raw",
        "merchant_normalized",
        "confidence",
        "note",
        "raw_image_url",
        "raw_ocr_text",
        "raw_ocr_engine",
        "raw_llm_model",
    }
    unknown = set(updates) - allowed
    if unknown:
        raise ValidationError(
            f"unknown fields: {sorted(unknown)}",
            meta={"fields": sorted(unknown)},
        )

    if "currency" in updates:
        _validate_currency(updates["currency"])
    if "occurred_at" in updates and updates["occurred_at"] is not None:
        updates["occurred_at"] = _utc_datetime(updates["occurred_at"])
    if "amount_cents" in updates:
        _validate_amount(updates["amount_cents"])
    if "source" in updates:
        _validate_source(updates["source"])
    if "category_id" in updates:
        _ensure_category_exists(session, updates["category_id"])
    if "account_id" in updates:
        if updates["account_id"] is None:
            raise ValidationError("accountId cannot be null", meta={"field": "accountId"})
        _ensure_account_writable(session, updates["account_id"])

    for k, v in updates.items():
        setattr(txn, k, v)
    session.flush()
    return txn


def delete_transaction(session: Session, transaction_id: str) -> None:
    txn = get_transaction(session, transaction_id)
    session.delete(txn)
    session.flush()


# ────────────────────────────────── list + pagination ─────────────────────────────────


def list_transactions(
    session: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    categories: Iterable[str] | None = None,
    accounts: Iterable[str] | None = None,
    types: Iterable[str] | None = None,
    search: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    cursor: str | None = None,
) -> TransactionPage:
    """Return a page of transactions sorted by `(occurred_at DESC, id DESC)`.

    Cursor is opaque: base64(JSON({"o": iso_datetime, "i": id})). Decoded into
    a tuple comparison filter `(occurred_at, id) < (cursor_o, cursor_i)` that
    yields the strictly-older page.

    The HTTP layer (M4) maps its query params `from/to/category/q` to these.
    """
    limit = max(1, min(limit, _MAX_LIMIT))

    stmt = select(Transaction)
    if start is not None:
        stmt = stmt.where(Transaction.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(Transaction.occurred_at <= end)
    if categories:
        ids = list(categories)
        if ids:
            stmt = stmt.where(Transaction.category_id.in_(ids))
    if accounts:
        account_ids = list(accounts)
        if account_ids:
            stmt = stmt.where(Transaction.account_id.in_(account_ids))
    if types:
        type_values = list(types)
        if type_values:
            stmt = stmt.where(Transaction.type.in_(type_values))
    if search:
        needle = f"%{search.strip().lower()}%"
        stmt = stmt.where(func.lower(Transaction.merchant).like(needle))
    if cursor is not None:
        cur_occ, cur_id = _decode_cursor(cursor)
        # (occurred_at, id) < (cur_occ, cur_id) — strict descending pagination.
        stmt = stmt.where(
            or_(
                Transaction.occurred_at < cur_occ,
                and_(Transaction.occurred_at == cur_occ, Transaction.id < cur_id),
            )
        )

    stmt = stmt.order_by(Transaction.occurred_at.desc(), Transaction.id.desc()).limit(limit + 1)

    rows = list(session.scalars(stmt).all())
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1].occurred_at, page[-1].id) if has_more and page else None
    return TransactionPage(items=page, next_cursor=next_cursor)


# ─────────────────────────────────── internals ────────────────────────────────────────


def _validate_currency(currency: str) -> None:
    if not isinstance(currency, str) or not _CURRENCY_RE.fullmatch(currency):
        raise ValidationError(
            f"currency must be a 3-letter ISO code, got {currency!r}",
            meta={"field": "currency"},
        )


def _utc_datetime(value: datetime) -> datetime:
    """SQLite drops offsets; normalize aware inputs before storage. Naive is UTC."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _validate_amount(amount_cents: int) -> None:
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise ValidationError("amountCents must be an integer", meta={"field": "amountCents"})
    if amount_cents == 0:
        raise ValidationError("amountCents must be non-zero", meta={"field": "amountCents"})


def _validate_source(source: str) -> None:
    if source not in ("photo", "manual", "receipt", "screenshot", "csv", "slash", "agent", "adjustment"):
        raise ValidationError(
            f"unsupported transaction source: {source!r}",
            meta={"field": "source"},
        )


def _validate_type(type: str) -> None:
    if type not in TRANSACTION_TYPES:
        raise ValidationError(
            f"type must be one of {TRANSACTION_TYPES}, got {type!r}",
            meta={"field": "type"},
        )


def _ensure_account_writable(session: Session, account_id: str) -> None:
    account = session.get(Account, account_id)
    if account is None:
        raise ValidationError(
            f"account {account_id!r} does not exist",
            meta={"field": "accountId", "accountId": account_id},
        )
    if account.archived:
        raise ArchivedAccountError(
            f"account {account_id!r} is archived",
            meta={"field": "accountId", "accountId": account_id},
        )


def _ensure_category_exists(session: Session, category_id: str) -> None:
    exists = session.get(Category, category_id)
    if exists is None:
        raise ValidationError(
            f"category {category_id!r} does not exist",
            meta={"field": "categoryId", "categoryId": category_id},
        )


def _encode_cursor(occurred_at: datetime, id: str) -> str:
    payload = json.dumps({"o": occurred_at.isoformat(), "i": id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        return datetime.fromisoformat(payload["o"]), payload["i"]
    except (ValueError, KeyError) as exc:
        raise ValidationError("invalid cursor", meta={"field": "cursor"}) from exc
