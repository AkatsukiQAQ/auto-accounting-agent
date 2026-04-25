from __future__ import annotations

from typing import Optional

from backend.api.schemas.base import CamelModel
from backend.api.schemas.transaction import TransactionCreate


class ImportPhotoData(CamelModel):
    preview_transaction: TransactionCreate
    confidence: float
    ocr_text: str
    ocr_engine: str
    llm_model: Optional[str] = None
