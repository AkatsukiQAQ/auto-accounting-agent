"""Dev helper — copy OPENAI_API_KEY from .env into user_settings.apiKeys.openai.

Decision #6: the server only reads the key from SQLite, not from env. That's
fine in production where the user sets it via the Settings UI, but during
development you want a one-shot way to push your .env key into the local DB
so you don't have to PATCH /api/settings by hand after every `make db-reset`.

Usage: `make seed-api-key` (or `uv run python -m backend.scripts.seed_api_key`).
"""
from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from backend.api.config import AppConfig
from backend.db.session import build_engine, build_session_factory
from backend.services.settings import update_settings


def main() -> int:
    load_dotenv()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key == "sk-replace-me":
        print("✗ OPENAI_API_KEY is missing or placeholder in .env", file=sys.stderr)
        return 1

    config = AppConfig()
    engine = build_engine(config.database_url)
    factory = build_session_factory(engine)

    try:
        with factory() as session:
            patch: dict[str, Any] = {"apiKeys": {"openai": key}}
            update_settings(session, patch)
            session.commit()
    finally:
        engine.dispose()

    print(f"✓ OPENAI_API_KEY (…{key[-4:]}) written to user_settings in {config.database_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
