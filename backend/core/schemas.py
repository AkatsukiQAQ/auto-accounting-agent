from __future__ import annotations

import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OCR_Receipt(BaseModel):
    raw_text: str = Field(
        ..., description="Full verbatim transcription of text, preserving line breaks for one receipt"
    )


class OCR_Results(BaseModel):
    ocr_results: List[OCR_Receipt] = Field(
        ..., description="OCR result for all receipts found in the image"
    )


class ParsedReceipt(BaseModel):
    raw_text: str = Field(
        ..., description="Full verbatim transcription of text, preserving line breaks of one receipt"
    )
    currency: Optional[str] = Field(None, description="Detected currency code, e.g. USD, CNY, JPY")
    amount: Optional[float] = Field(None, description="Detected amount")
    date: Optional[str] = Field(None, description="Detected date in YYYY-MM-DD format")
    time: Optional[str] = Field(None, description="Detected time in HH:MM format")
    merchant: Optional[str] = Field(None, description="Detected merchant name")


class ParsedOcrResult(BaseModel):
    parsed_ocr_results: List[ParsedReceipt] = Field(
        ..., description="Parsed results for all receipts"
    )


class Subcategory(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    parent_name: str
    keywords: List[str]
    regex: Optional[re.Pattern] = None


class Category(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    keywords: List[str]
    sub_categories: Optional[List[Subcategory]] = None
    regex: Optional[re.Pattern] = None


class ReceiptClassification(BaseModel):
    idx: int = Field(..., description="Pre-set idx of the receipt.")
    category: str = Field(..., description="Main category of the receipt.")
    sub_category: Optional[str] = Field(
        None,
        description="Sub-category of the receipt. None if no sub-category matched.",
    )
    matched: bool = Field(
        ...,
        description="Whether this receipt is matched. False if neither category nor sub_category matched.",
    )
    keyword: Optional[str] = Field(
        None, description="Keyword that matched the category or sub_category."
    )


class ClassificationResult(BaseModel):
    classification_results: List[ReceiptClassification] = Field(
        ..., description="Classification results for all receipts"
    )
