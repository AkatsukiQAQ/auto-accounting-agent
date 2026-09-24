from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data
from backend.api.schemas.merchant import NormalizeIn, NormalizeOut
from backend.services.normalization import normalize

router = APIRouter(prefix="/api/normalize", tags=["merchants"])


@router.post("", response_model=Data[NormalizeOut])
def preview_(body: NormalizeIn, session: Session = Depends(get_session)) -> Data[NormalizeOut]:
    """Stateless preview of what the engine would decide — writes NOTHING
    (alias hit counters are not incremented, no commit)."""
    outcome = normalize(session, body.raw, count_alias_hits=False)
    return Data(
        data=NormalizeOut(
            normalized=outcome.normalized,
            merchant_id=outcome.merchant_id,
            matched_by=outcome.matched_by,
        )
    )
