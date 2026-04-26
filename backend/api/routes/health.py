from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.config import AppConfig
from backend.api.deps import get_config
from backend.api.schemas.base import Data
from backend.api.schemas.health import HealthOut

router = APIRouter()


@router.get("/api/health", response_model=Data[HealthOut])
def get_health(config: AppConfig = Depends(get_config)) -> Data[HealthOut]:
    return Data(data=HealthOut(ok=True, version=config.version))
