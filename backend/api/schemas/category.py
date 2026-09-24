from __future__ import annotations

from datetime import datetime
from typing import Optional

from backend.api.schemas.base import CamelModel


class CategoryOut(CamelModel):
    id: str
    label: str
    color_bg: str
    color_dot: str
    icon: str | None
    icon_image_url: str | None
    keywords: list[str]
    auto_assign: bool
    sort_order: int
    created_at: datetime


class CategoryCreate(CamelModel):
    id: str
    label: str
    color_bg: str
    color_dot: str
    icon: Optional[str] = None
    keywords: Optional[list[str]] = None
    auto_assign: bool = True
    sort_order: Optional[int] = None


class CategoryUpdate(CamelModel):
    label: Optional[str] = None
    color_bg: Optional[str] = None
    color_dot: Optional[str] = None
    icon: Optional[str] = None
    icon_image_url: Optional[str] = None
    keywords: Optional[list[str]] = None
    auto_assign: Optional[bool] = None
    sort_order: Optional[int] = None
