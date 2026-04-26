from __future__ import annotations

from backend.api.schemas.base import CamelModel


class HealthOut(CamelModel):
    ok: bool
    version: str
