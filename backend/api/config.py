"""Application startup configuration.

Kept distinct from `backend/services/settings.py` (which is the per-user
settings stored in the DB). This module holds process-level bootstrap
values — DB URL, CORS origins, LLM model name, storage paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    database_url: str = "sqlite:///./mita.db"
    llm_model: str = "gpt-5-nano"
    image_storage_dir: Path = Path("./storage/images")
    image_public_base_url: str = "/media"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    version: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v: Any) -> Any:
        """Let CORS_ORIGINS env var be a comma-separated string."""
        if isinstance(v, str):
            return tuple(p.strip() for p in v.split(",") if p.strip())
        return v
