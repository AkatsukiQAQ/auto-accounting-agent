from __future__ import annotations

from typing import Optional

from backend.api.schemas.base import CamelModel
from backend.api.schemas.transaction import TransactionCreate


class ImportPhotoData(CamelModel):
    """Response from POST /api/import/photo.

    A single uploaded image can contain multiple receipts (e.g. a PayPay
    transaction-history screenshot). The pipeline returns one draft per
    receipt; the frontend renders them as a list and lets the user edit /
    drop each before committing.
    """

    preview_transactions: list[TransactionCreate]
    confidences: list[float]  # parallel to preview_transactions
    ocr_text: str             # full image OCR (joined across receipts)
    ocr_engine: str
    llm_model: Optional[str] = None
