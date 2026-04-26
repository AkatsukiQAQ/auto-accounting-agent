from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.transaction import (
    RawOut,
    TransactionCreate,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdate,
)
from backend.db.models import Transaction
from backend.services.transactions import (
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _to_out(t: Transaction) -> TransactionOut:
    has_raw = any(
        x is not None
        for x in (t.raw_image_url, t.raw_ocr_text, t.raw_ocr_engine, t.raw_llm_model)
    )
    raw = (
        RawOut(
            image_url=t.raw_image_url,
            ocr_text=t.raw_ocr_text,
            ocr_engine=t.raw_ocr_engine,
            llm_model=t.raw_llm_model,
        )
        if has_raw
        else None
    )
    return TransactionOut(
        id=t.id,
        occurred_at=t.occurred_at,
        created_at=t.created_at,
        merchant=t.merchant,
        amount_cents=t.amount_cents,
        currency=t.currency,
        category_id=t.category_id,
        source=t.source,  # type: ignore[arg-type]
        confidence=t.confidence,
        note=t.note,
        raw=raw,
    )


def _flatten_create(body: TransactionCreate) -> dict[str, Any]:
    data = body.model_dump(by_alias=False, exclude={"raw"})
    if body.raw is not None:
        for k, v in body.raw.model_dump(by_alias=False).items():
            data[f"raw_{k}"] = v
    return data


def _flatten_update(body: TransactionUpdate) -> dict[str, Any]:
    fields_set = body.model_fields_set
    data = body.model_dump(by_alias=False, exclude_unset=True, exclude={"raw"})
    if "raw" in fields_set and body.raw is not None:
        for k, v in body.raw.model_dump(by_alias=False, exclude_unset=True).items():
            data[f"raw_{k}"] = v
    return data


@router.get("", response_model=TransactionListResponse)
def list_(
    session: Session = Depends(get_session),
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    category: Optional[str] = Query(None, description="Comma-separated category ids"),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None),
) -> TransactionListResponse:
    categories = [c.strip() for c in category.split(",") if c.strip()] if category else None
    page = list_transactions(
        session,
        start=date_from,
        end=date_to,
        categories=categories,
        search=q,
        limit=limit,
        cursor=cursor,
    )
    return TransactionListResponse(
        data=[_to_out(t) for t in page.items],
        next_cursor=page.next_cursor,
    )


@router.get("/{transaction_id}", response_model=Data[TransactionOut])
def get_(transaction_id: str, session: Session = Depends(get_session)) -> Data[TransactionOut]:
    return Data(data=_to_out(get_transaction(session, transaction_id)))


@router.post("", response_model=Data[TransactionOut], status_code=status.HTTP_201_CREATED)
def create_(
    body: TransactionCreate, session: Session = Depends(get_session)
) -> Data[TransactionOut]:
    txn = create_transaction(session, **_flatten_create(body))
    session.commit()
    return Data(data=_to_out(txn))


@router.patch("/{transaction_id}", response_model=Data[TransactionOut])
def update_(
    transaction_id: str,
    body: TransactionUpdate,
    session: Session = Depends(get_session),
) -> Data[TransactionOut]:
    txn = update_transaction(session, transaction_id, **_flatten_update(body))
    session.commit()
    return Data(data=_to_out(txn))


@router.delete("/{transaction_id}", response_model=Data[OkOut])
def delete_(
    transaction_id: str, session: Session = Depends(get_session)
) -> Data[OkOut]:
    delete_transaction(session, transaction_id)
    session.commit()
    return Data(data=OkOut())
