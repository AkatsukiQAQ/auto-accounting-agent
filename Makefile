.PHONY: dev stop restart db-migrate db-reset test seed-api-key help

PORT ?= 8000

help:
	@echo "Common tasks:"
	@echo "  make dev           Start uvicorn with auto-reload (kills stale :$(PORT) first)"
	@echo "  make stop          Force-release port $(PORT)"
	@echo "  make restart       stop + dev"
	@echo "  make db-migrate    alembic upgrade head"
	@echo "  make db-reset      Wipe mita.db and re-migrate (dev only)"
	@echo "  make test          uv run pytest"
	@echo "  make seed-api-key  Copy OPENAI_API_KEY from .env into user_settings.apiKeys.openai"

dev:
	@./scripts/dev.sh

stop:
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || echo "No process on :$(PORT)"

restart: stop dev

db-migrate:
	@uv run alembic upgrade head

db-reset:
	@rm -f mita.db mita.db-wal mita.db-shm
	@uv run alembic upgrade head

test:
	@uv run pytest

seed-api-key:
	@uv run python -m backend.scripts.seed_api_key
