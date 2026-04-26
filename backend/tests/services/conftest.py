from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db.base import Base
from backend.db.models import Category, Transaction, UserSettings  # noqa: F401  (register tables)
from backend.db.seeders.categories import seed_categories
from backend.services.pipeline.config import PipelineConfig
from backend.services.pipeline.llm import PipelineLLM
from backend.services.pipeline.stages import StageContext


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = factory()
    try:
        seed_categories(s)
        s.flush()
        yield s
    finally:
        s.close()


@pytest.fixture()
def pipeline_config() -> PipelineConfig:
    return PipelineConfig(
        accepted_currencies=("USD", "JPY", "EUR"),
        symbol_defaults={"¥": "JPY", "$": "USD"},
    )


@pytest.fixture()
def make_ctx(
    session: Session, pipeline_config: PipelineConfig
) -> Callable[[PipelineLLM], StageContext]:
    def _make(llm: PipelineLLM) -> StageContext:
        return StageContext(llm=llm, session=session, config=pipeline_config)

    return _make
