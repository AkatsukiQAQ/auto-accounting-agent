"""Transaction CRUD service.

Pure business logic — no HTTP, no Pydantic DTOs, no auth. The API layer (M4)
converts request bodies to/from these call signatures. Inputs and outputs use
snake_case DB column names; camelCase conversion lives in `api/schemas/`.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.db.models import Category, Transaction
from backend.services.errors import NotFoundError, ValidationError
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
    merchant: str,
    amount_cents: int,
    currency: str,
    category_id: str,
    source: str,
    confidence: float | None = None,
    note: str | None = None,
    raw_image_url: str | None = None,
    raw_ocr_text: str | None = None,
    raw_ocr_engine: str | None = None,
    raw_llm_model: str | None = None,
) -> Transaction:
    _validate_currency(currency)
    _validate_amount(amount_cents)
    _validate_source(source)
    _ensure_category_exists(session, category_id)

    txn = Transaction(
        id=new_transaction_id(),
        occurred_at=occurred_at,
        merchant=merchant,
        amount_cents=amount_cents,
        currency=currency,
        category_id=category_id,
        source=source,
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

    allowed = {
        "occurred_at",
        "merchant",
        "amount_cents",
        "currency",
        "category_id",
        "source",
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
    if "amount_cents" in updates:
        _validate_amount(updates["amount_cents"])
    if "source" in updates:
        _validate_source(updates["source"])
    if "category_id" in updates:
        _ensure_category_exists(session, updates["category_id"])

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


def _validate_amount(amount_cents: int) -> None:
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        raise ValidationError("amountCents must be an integer", meta={"field": "amountCents"})
    if amount_cents == 0:
        raise ValidationError("amountCents must be non-zero", meta={"field": "amountCents"})


def _validate_source(source: str) -> None:
    if source not in ("photo", "manual"):
        raise ValidationError(
            f"source must be 'photo' or 'manual', got {source!r}",
            meta={"field": "source"},
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
