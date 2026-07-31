from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.api.schemas.base import CamelModel
from backend.api.schemas.transaction import TransactionOut


class TransferCreate(CamelModel):
    from_account_id: str
    to_account_id: str
    amount_cents: int
    occurred_at: datetime
    note: Optional[str] = None


class TransferOut(CamelModel):
    out_transaction: TransactionOut
    in_transaction: TransactionOut
    transfer_group_id: str
