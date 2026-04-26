<div align="center">

# Auto-Accounting Agent

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Phase](https://img.shields.io/badge/phase-1%20done-success)
![Tests](https://img.shields.io/badge/backend%20tests-168%20passing-success)

**A personal-finance app that turns a screenshot of your payment app into structured ledger entries.**

</div>

> **Co-built with Claude.** This project is developed end-to-end in pair-programming sessions with [Claude Code](https://claude.com/claude-code) — design plans, implementation, tests, and dev logs all happen in conversation. Commits are co-authored. The architecture and decision history are recorded under [`docs/dev_log/`](./docs/dev_log/) so any new session (human or AI) can pick up where the last one left off.

<!-- --- -->

## Table of Contents

1. [Introduction](#introduction)
2. [Status](#status)
3. [Architecture](#architecture)
4. [Usage](#usage)
   - [Installation](#installation)
   - [Run the API only](#api_only)
   - [Run the full stack](#full_stack)
5. [Roadmap](#roadmap)

<!-- --- -->

## Introduction <a name="introduction"></a>

Manual bookkeeping is tedious — most accounting apps want you to type every coffee, every taxi, every line item. **Mita Finance** flips it: snap a screenshot of your PayPay / Alipay / WeChat Pay / receipt, drop it on the app, and the OCR + classification pipeline produces draft transactions you can confirm in one click.

The pipeline is deterministic three stages — OCR → parse → classify — running on `gpt-5-nano` via the OpenAI Responses API. A regex layer short-circuits common merchants so most receipts never hit the LLM for classification. Multi-receipt screenshots (typical for monthly account history) produce one draft per receipt; a "quick-import" mode auto-saves high-confidence drafts and only asks you to confirm the ambiguous ones.

<!-- --- -->

## Status <a name="status"></a>

Phase 1 is **complete and runnable end-to-end** — backend, frontend, real OpenAI smoke-tested on multi-receipt PayPay screenshots.

| Layer | What's there | Tests |
|---|---|---|
| `backend/core/` | Pure pipeline functions (OCR / parse / classify), framework-free | 62 |
| `backend/db/` | SQLAlchemy models + Alembic + idempotent seeder | 8 |
| `backend/services/` | Pipeline orchestrator + CRUD + settings | 58 |
| `backend/api/` | FastAPI app, 15 endpoints, camelCase DTOs | 40 |
| `frontend/` | Vite + React 19 + TS + Tailwind 4, 5 screens, TanStack Query | — |
| **Total** | | **168 backend tests passing** |

The frontend ships the prototype's "warm cream paper" design system (Kalam + Indie Flower handwritten fonts, terracotta/olive-tone semantics, paper-bg radial gradients) — see [`design/screenshots/dashboard-a.png`](./design/screenshots/dashboard-a.png) for the reference.

<!-- --- -->

## Architecture <a name="architecture"></a>

```
backend/
  core/      ─ pure functions (OCR prompts, regex classifier, currency parser)
  db/        ─ SQLAlchemy models, Alembic migrations, category seeder
  services/  ─ ImportPipeline, transactions/categories/settings CRUD, errors
  api/       ─ FastAPI routes, Pydantic DTOs, dependency injection
  scripts/   ─ dev helpers (seed-api-key, etc.)
  tests/     ─ pytest suites mirroring the layer order

frontend/
  src/
    lib/         ─ fetch wrapper, types, formatters
    hooks/       ─ TanStack Query bindings per resource
    components/  ─ ui primitives, layout, charts, import flow, transaction form
    pages/       ─ Dashboard / Records / Import / Categories / Settings
    router.tsx   ─ react-router-dom v7 routes
  index.html

design/        ─ phase-by-phase design docs + reference screenshots
docs/dev_log/  ─ per-session development logs (cross-machine handoff)
```

Strict layer order: `core/` ← `services/` ← `api/`. Pipeline LLM calls go through the `PipelineLLM` Protocol so tests inject a `FakePipelineLLM` and never hit OpenAI.

<!-- --- -->

## Usage <a name="usage"></a>

### Installation <a name="installation"></a>

**1. Clone**
```bash
git clone https://github.com/AkatsukiQAQ/auto-accounting-agent
cd auto-accounting-agent
```

**2. Backend environment**

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management. `pyproject.toml` + `uv.lock` are the source of truth.

```bash
pip install uv      # one-off
uv sync --dev       # creates .venv/ and installs runtime + dev deps
```

**3. Configure environment**

```bash
cp .env.example .env
# edit .env, set OPENAI_API_KEY=sk-...
```

`.env` is git-ignored. The running server reads the key from SQLite (`user_settings.apiKeys.openai`), **not** from env — `.env` is only used by the `make seed-api-key` dev helper to bootstrap the DB.

**4. Run tests**
```bash
make test           # all 168 backend tests should pass
```

### Run the API only <a name="api_only"></a>

```bash
make db-migrate     # alembic upgrade head — creates mita.db
make seed-api-key   # copy OPENAI_API_KEY from .env into the DB
make dev            # uvicorn on :8000 with auto-reload
```

- API: `http://localhost:8000/api/*`
- OpenAPI docs: `http://localhost:8000/docs`
- Uploaded images: `http://localhost:8000/media/<YYYY>/<MM>/<id>.<ext>`

Quick test: `curl -F image=@path/to/receipt.png http://localhost:8000/api/import/photo`

### Run the full stack <a name="full_stack"></a>

The frontend is a Vite + React 19 + TypeScript app under `frontend/`.

```bash
# Terminal 1 — backend
make db-migrate
make seed-api-key
make dev                   # :8000

# Terminal 2 — frontend
cd frontend
cp .env.example .env       # default VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev                # :5173
```

Open `http://localhost:5173`. Five screens: Dashboard / Records / Import / Categories / Settings.

If you skipped `make seed-api-key`, set the OpenAI key inside the app at **Settings → API Keys** before using photo import.

#### Make targets

| Target | What it does |
|---|---|
| `make dev` | start uvicorn (kills stale port first) |
| `make stop` | force-release port 8000 |
| `make restart` | stop + dev |
| `make db-migrate` | `alembic upgrade head` |
| `make db-reset` | wipe `mita.db` + re-migrate (dev only) |
| `make test` | `uv run pytest` |
| `make seed-api-key` | copy `.env` key into the DB |

<!-- --- -->

## Roadmap <a name="roadmap"></a>

Phase definitions and decision history live in [`design/`](./design/) and per-session [`docs/dev_log/`](./docs/dev_log/).

- ✅ **Phase 0** — `backend/core/` extracted as a framework-free library.
- ✅ **Phase 1** — FastAPI service + 5-screen frontend, real-LLM end-to-end.
  - ✨ Beyond the original spec: multi-receipt support, quick-import mode, per-draft carousel with Save/Skip/Previous, processing queue with state-lifted tab-switch fix.
- ⏳ **Dogfood Phase 1** — using it daily before opening Phase 2.
- 🔮 **Phase 2 backend** — accounts, merchant normalization, transfers, budgets, recurring rules, `review_queue` table, ReviewRouter.
- 🔮 **Phase 2 frontend** — Accounts / Budget / Recurring / Review screens (the "Soon" sidebar slots).
- 🔮 **Phase 3** — chatbot panel (LangChain returns), dark mode, i18n (zh/ja), ⌘K command palette, correction-learning rules.

For a fresh contributor (or a fresh Claude session): start by reading the latest [`docs/dev_log/`](./docs/dev_log/) entry — it doubles as a sticky-decisions handoff.

<!-- --- -->

## License

MIT. See [LICENSE](./LICENSE).
