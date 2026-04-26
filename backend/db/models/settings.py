from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # always 1
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
