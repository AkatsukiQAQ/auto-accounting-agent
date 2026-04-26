from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api import errors as api_errors
from backend.api.config import AppConfig
from backend.api.routes import categories, health, imports, settings, transactions
from backend.db.seeders.categories import seed_categories
from backend.db.session import build_engine, build_session_factory


def create_app(
    config: AppConfig | None = None,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    """Build the FastAPI app. Tests pass a pre-built `session_factory` bound to
    a shared in-memory SQLite engine; production lets it fall through to
    `build_engine(config.database_url)`.
    """
    config = config or AppConfig()

    owns_engine = session_factory is None
    engine: Engine | None = None
    if owns_engine:
        engine = build_engine(config.database_url)
        session_factory = build_session_factory(engine)

    # StaticFiles insists the directory exists at mount time — this is synchronous,
    # runs before lifespan, so we can't rely on lifespan to create it.
    config.image_storage_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        with session_factory() as s:
            seed_categories(s)
            s.commit()
        yield
        if owns_engine and engine is not None:
            engine.dispose()

    app = FastAPI(title="Mita API", version=config.version, lifespan=lifespan)
    app.state.config = config
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_errors.register(app)

    app.mount(
        config.image_public_base_url,
        StaticFiles(directory=config.image_storage_dir),
        name="media",
    )

    app.include_router(health.router)
    app.include_router(transactions.router)
    app.include_router(categories.router)
    app.include_router(imports.router)
    app.include_router(settings.router)

    return app


app = create_app()
