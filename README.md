<div align="center">

# Auto-Accounting Agent
![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
</div>

// TODO: Add demo result here


<!-- --- -->

## Table of Contents
1. [Introduction](#introduction)
2. [Usage](#usage)
   - [Installation](#installation)
   - [Quick Start](#quick_start)


<!-- --- -->

## Introduction <a name="introduction"></a>
Accounting, as a means of expense management, is essential in daily life. However, accounting software on the market requires users to manually fill in for each income and expense. For daily life, we may have dozens of expenses every day for purchasing daily necessities and food. Therefore, manual accounting is a very troublesome thing.

This project has built an agent that can help users **automate the accounting process**, allowing users to complete the accounting of multiple income and expenses through very simple operations.


<!-- --- -->

## Usage <a name="usage"></a>
### Installation <a name="installation"></a>
**1. Clone the repository**
```bash
git clone https://github.com/AkatsukiQAQ/auto-accounting-agent
cd auto-accounting-agent
```

**2. Environment setup**

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. `pyproject.toml` + `uv.lock` are source of truth; there is no `requirements.txt`.

```bash
# Install uv if you don't have it (one-off)
pip install uv

# Create .venv/ and install runtime + dev deps (pinned by uv.lock)
uv sync --dev
```

**PyCharm:** point **Settings → Project → Python Interpreter** at `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux). PyCharm 2024.1+ can also select the uv interpreter type directly from `pyproject.toml`.

**3. Configure environment**

Copy `.env.example` to `.env` and fill in your OpenAI key:
```bash
cp .env.example .env
# then edit .env: set OPENAI_API_KEY=sk-...
```

`.env` is git-ignored. The key is only used by the dev helper (`make seed-api-key`) — the server itself reads the key from the SQLite `user_settings` table, not from env. See "Quick Start" step 3.

**4. Run tests**
```bash
make test
```

All 167 tests should pass (core + db + services + api).

### Quick Start <a name="quick_start"></a>

**1. Initialize the database**
```bash
make db-migrate   # alias for `uv run alembic upgrade head`
```

Creates `mita.db` in the repo root. On first server startup, 9 default categories are auto-seeded from the pipeline's legacy YAML.

**2. Start the API server**
```bash
make dev
```

Kills any stale process on port 8000, then runs `uvicorn backend.api.main:app --reload`.
- API: `http://localhost:8000/api/*`
- OpenAPI docs: `http://localhost:8000/docs`
- Uploaded images: `http://localhost:8000/media/<YYYY>/<MM>/<id>.<ext>`

**3. (Dev only) Push your OpenAI key into the DB**

The pipeline reads the key from SQLite (`user_settings.apiKeys.openai`), not from env — this keeps it scoped to the user's machine. In the frontend flow the user sets it on the Settings page (`PATCH /api/settings` with `{"apiKeys": {"openai": "sk-..."}}`). For local dev, a shortcut:

```bash
make seed-api-key
```

This reads `OPENAI_API_KEY` from `.env` and upserts it into the DB via the normal service layer.

**4. Import a receipt**
```bash
curl -X POST http://localhost:8000/api/import/photo \
     -F "image=@path/to/receipt.png" | python -m json.tool
```

Response is a draft `previewTransaction`. The frontend lets the user edit it, then commits via `POST /api/transactions`.

**5. Common make targets**

| Target | What it does |
|---|---|
| `make dev` | start uvicorn with auto-reload (kills stale port first) |
| `make stop` | force-release port 8000 |
| `make restart` | stop + dev |
| `make db-migrate` | `alembic upgrade head` |
| `make db-reset` | wipe `mita.db` + re-migrate (dev only) |
| `make test` | `uv run pytest` |
| `make seed-api-key` | copy `.env` key into the DB |

<!-- --- -->

## TO-DO & Next Step <a name="todo"></a>
- [ ] Phase 2 backend: accounts, merchant normalization, transfers, budgets, recurring rules, review queue
- [ ] Frontend Phase 1: wire the 5 screens to the real API (currently mocked against the prototype)


<!-- --- -->