"""FastAPI dependency providers.

The app factory (`create_app`) attaches `session_factory` and `config` to
`app.state`; these providers read from there. Tests override individual
providers via `app.dependency_overrides`.
"""
from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.api.config import AppConfig
from backend.services.errors import ApiKeyNotConfiguredError
from backend.services.pipeline import (
    ImportPipeline,
    OpenAIPipelineLLM,
    PipelineConfig,
    PipelineLLM,
    build_default_pipeline,
    load_default_pipeline_config,
)
from backend.services.settings import get_settings


@lru_cache
def _cached_config() -> AppConfig:
    return AppConfig()


def get_config(request: Request) -> AppConfig:
    """Return the app-scoped config if set by `create_app`, else the env-loaded default."""
    cfg = getattr(request.app.state, "config", None)
    return cfg if cfg is not None else _cached_config()


def get_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    s = factory()
    try:
        yield s
    finally:
        s.close()


@lru_cache
def get_pipeline_config() -> PipelineConfig:
    return load_default_pipeline_config()


@lru_cache
def get_pipeline() -> ImportPipeline:
    """Stateless orchestrator — one instance is fine for the whole app."""
    return build_default_pipeline()


def get_llm(
    session: Session = Depends(get_session),
    config: AppConfig = Depends(get_config),
) -> PipelineLLM:
    """Build an OpenAI LLM client from the user_settings-stored API key.

    Decision #6: API key lives only in SQLite `user_settings.apiKeys.openai`,
    never in env. Missing key → 400 so frontend can redirect to /settings.
    """
    settings_data = get_settings(session)
    session.commit()  # get_settings may have created the default row
    key = (settings_data.get("apiKeys") or {}).get("openai")
    if not key:
        raise ApiKeyNotConfiguredError(
            "OpenAI API key is not configured. Set it on the Settings page first.",
        )
    return OpenAIPipelineLLM(api_key=key, model=config.llm_model)
