from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data
from backend.services.settings import get_settings, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=Data[dict[str, Any]])
def get_(session: Session = Depends(get_session)) -> Data[dict[str, Any]]:
    data = get_settings(session)
    session.commit()  # first read may create the default row
    return Data(data=data)


@router.patch("", response_model=Data[dict[str, Any]])
def patch_(
    body: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
) -> Data[dict[str, Any]]:
    merged = update_settings(session, body)
    session.commit()
    return Data(data=merged)
