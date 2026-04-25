from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.config import AppConfig
from backend.api.deps import get_llm
from backend.api.main import create_app
from backend.db.base import Base
from backend.db.models import Category, Transaction, UserSettings  # noqa: F401
from backend.tests.services.fakes import FakePipelineLLM


@pytest.fixture()
def engine() -> Iterator[Engine]:
    """Shared in-memory SQLite — StaticPool + check_same_thread=False so every
    FastAPI request sees the same DB within one test."""
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    try:
        yield e
    finally:
        e.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """For tests that want to inspect the DB directly (write a fixture, check a row)."""
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def fake_llm() -> FakePipelineLLM:
    """Empty fake; tests mutate `.responses` to seed canned schemas."""
    return FakePipelineLLM(responses={}, model_name="fake-model")


@pytest.fixture()
def test_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database_url="sqlite:///:memory:",  # unused — session_factory is injected
        image_storage_dir=tmp_path / "storage" / "images",
        cors_origins=("http://testserver",),
        llm_model="fake-model",
    )


@pytest.fixture()
def app(test_config, session_factory, fake_llm):
    """Create a fresh FastAPI app per test. Lifespan seeds categories automatically."""
    a = create_app(config=test_config, session_factory=session_factory)
    a.dependency_overrides[get_llm] = lambda: fake_llm
    yield a
    a.dependency_overrides.clear()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    # raise_server_exceptions=False so our `@app.exception_handler(Exception)`
    # handler actually gets a chance to return a 500 response; otherwise
    # TestClient re-raises unhandled exceptions into the test and the handler
    # never runs.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ─────────────────────────── handy constants ────────────────────────────

# Minimal valid PNG header — enough to pass the magic-byte check in imports route.
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

# Value that fails the magic-byte check but passes content-type.
FAKE_PNG_BYTES = b"not a real png" + b"\x00" * 32
