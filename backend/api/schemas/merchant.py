from __future__ import annotations

from typing import Optional

from backend.api.schemas.base import CamelModel


class MerchantOut(CamelModel):
    id: str
    canonical_name: str
    aliases: list[str]
    default_category_id: Optional[str] = None
    logo_url: Optional[str] = None
    source: str


class MerchantCreate(CamelModel):
    canonical_name: str
    aliases: list[str] = []
    default_category_id: Optional[str] = None
    logo_url: Optional[str] = None


class MerchantUpdate(CamelModel):
    canonical_name: Optional[str] = None
    aliases: Optional[list[str]] = None
    default_category_id: Optional[str] = None
    logo_url: Optional[str] = None


class MerchantAliasOut(CamelModel):
    id: str
    raw_pattern: str
    match_type: str
    merchant_id: str
    applied_count: int


class MerchantAliasCreate(CamelModel):
    raw_pattern: str
    match_type: str
    merchant_id: str


class NormalizeIn(CamelModel):
    raw: str


class NormalizeOut(CamelModel):
    normalized: str
    merchant_id: Optional[str] = None
    matched_by: str
