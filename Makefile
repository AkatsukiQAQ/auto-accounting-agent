.PHONY: dev stop restart db-migrate db-reset test seed-api-key help

PORT ?= 8000

# Recipes must stay single plain commands (no pipes, redirects, or unix tools):
# make then spawns them directly without a shell, so targets work from both
# PowerShell (no bash/lsof/rm on PATH) and Git Bash. Anything fancier belongs
# in scripts/dev_utils.py.

define HELP_TEXT
Common tasks:
  make dev           Start uvicorn with auto-reload (kills stale :$(PORT) first)
  make stop          Force-release port $(PORT)
  make restart       stop + dev
  make db-migrate    alembic upgrade head
  make db-reset      Wipe mita.db and re-migrate (dev only)
  make test          uv run pytest
  make seed-api-key  Copy OPENAI_API_KEY from .env into user_settings.apiKeys.openai
endef

help:
	@$(info $(HELP_TEXT))uv run python -c pass

dev: stop
	uv run uvicorn backend.api.main:app --reload --host 127.0.0.1 --port $(PORT)

stop:
	@uv run python scripts/dev_utils.py free-port $(PORT)

restart: stop dev

db-migrate:
	@uv run alembic upgrade head

db-reset:
	@uv run python scripts/dev_utils.py clean-db
	@uv run alembic upgrade head

test:
	@uv run pytest

seed-api-key:
	@uv run python -m backend.scripts.seed_api_key