<div align="center">

<img src="docs/assets/finance_banner.png" alt="Mita Finance — your co-pilot for smarter spending" width="100%">

# Auto-Accounting Agent

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Phase](https://img.shields.io/badge/phase-V2%20Agent%20Core-success)
![Tests](https://img.shields.io/badge/backend%20tests-319%20passing-success)

**A budget-first personal finance app: plan your week or month, track spending, and see what remains.**

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

MITA Finance helps you compare planned, spent and remaining money across weekly and monthly budgets. Quick expenses and category-total adjustments support imperfect tracking, while receipt imports remain useful supporting evidence.

The pipeline is deterministic three stages — OCR → parse → classify — running on `gpt-5-nano` via the OpenAI Responses API. A regex layer short-circuits common merchants so most receipts never hit the LLM for classification. Multi-receipt screenshots (typical for monthly account history) produce one draft per receipt; a "quick-import" mode auto-saves high-confidence drafts and only asks you to confirm the ambiguous ones.

<!-- --- -->

## Status <a name="status"></a>

V2 Phase 1 **Budget Core** and the first V2 Phase 2 **Agent Core** milestones are implemented. Start on Dashboard, select Week or Month, create a plan at `/plan`, or open **Chat** to query and control the same deterministic budget services. Records, receipt Import, Categories and Settings remain available.

- Budget calculations, status, projections and category-total corrections run in deterministic Python/SQL services, without an LLM.
- Plan cloning copies allocations and targets. Weekly and monthly plans coexist; currency totals never mix.
- Records labels aggregate adjustments explicitly. A later import adds to existing spending; reconciliation is manual.
- Existing account/transfer infrastructure remains compatible but is not extended or promoted in navigation.
- Chat persists sessions and structured actions, supports deterministic slash commands, and requires explicit confirmation for natural-language writes.
- The planning agent can read four completed weeks, propose a complete next-week budget, let the user edit it, and atomically Apply/Cancel/Undo it.

See [Budget Core behavior and API](design/V2_PHASE_1_BUDGET_CORE.md), [product specification](design/V2_PRODUCT.md) and [development log](docs/dev_log/2026-09-22-budget-core.md). Historical V1 plans are snapshotted in [design/archive/v1](design/archive/v1/README.md).

Before running: `uv sync`, then `uv run alembic upgrade head`. This applies the forward migrations through `0009_chat_session_titles`; no database reset is required. Back up an existing local database before applying migrations.

Validation: `uv run pytest`, and in `frontend/`: `npm test`, `npm run build`. Frontend unit tests require Node 22.6+ for TypeScript stripping. Whole-repository `npm run lint` currently reports pre-existing errors in DonutChart and ImportPage; changed Budget Core files pass targeted lint.

The warm-paper design tokens, PaperCard, Button, CatPill, navigation shell and formatters are retained.

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
    pages/       ─ Dashboard / Chat / Plan / Records / Import / Categories / Settings
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
make test           # all backend tests should pass
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

Open `http://localhost:5173`. Six screens: Dashboard / Plan / Records / Import / Categories / Settings.

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

## Budget Chat — V2 Phase 2 Agent Core

Run `uv run alembic upgrade head`, then open **Chat** from the left navigation. Chat sessions,
messages and structured actions persist in SQLite. Natural-language budget changes show
an **Apply / Edit / Cancel** card; only Apply writes through the existing budget/ledger services.
The Dashboard and Records caches refresh after execution. Read questions use typed
deterministic services; Chat does not own financial arithmetic.

Configure the existing **Settings → API Keys → OpenAI** key for natural-language Chat.
`AGENT_MODEL` selects its model independently of receipt import's `LLM_MODEL`.
No key is needed for these deterministic commands:

```text
/spend 1800 food
/income 300000 salary
/budget food 12000 next-week
/set-spent food 8500 month
/summary month
/plan next-week
/help
/undo
```

Amounts above are major currency units in the profile currency. Use exact category IDs
or labels (quote multi-word labels); substitute `dining` if that category exists.
`/income` records actual income. `/undo` supports entries, adjustments, ordinary plan edits,
and the complete next-week planning proposal, with conflict checks.
After an uncertain connection failure, refresh the chat before resending a slash write.

For a complete next-week plan, ask naturally, for example: “Help me make a stricter budget
for next week.” The agent reads up to four completed weeks plus current week/month context,
then presents every category, its old/new amount, delta, reason, planned income, savings target,
and residual. Totals are computed by the deterministic planning service. Apply writes all
operations in one transaction; stale or partially invalid plans are rejected without mutation.
`/plan next-week` starts the same confirmation flow. While a plan is pending, a follow-up such
as “Make Food 12,000 and keep the rest” creates a complete replacement proposal and disables
the older card, so only one next-week plan remains actionable. `/help` lists commands without
requiring an API key.

See [`design/V2_PHASE_2_AGENT.md`](./design/V2_PHASE_2_AGENT.md) for tool contracts,
API/stream events, confirmation guarantees and the end-to-end demo. Standard tests use
model stubs and make no paid model calls.

<!-- --- -->

## Roadmap <a name="roadmap"></a>

Phase definitions and decision history live in [`design/`](./design/) and per-session [`docs/dev_log/`](./docs/dev_log/).

- **V1 foundation preserved:** receipt pipeline, transaction/category/settings CRUD and the MITA design system.
- **V2 Phase 1 implemented:** deterministic Budget Core, Dashboard and Plan.
- **V2 Phase 2 Agent Core implemented:** global Chat, typed tools, deterministic commands, confirmation, action audit and complete next-week planning with Edit/Apply/Cancel/Undo.
- **Next:** dogfood the planning loop; provider token streaming and longer-history planning UX remain follow-ups.
- Accounts, net worth, recurring workers, review queues and bank sync are not priorities in this phase.

For a fresh contributor (or a fresh Claude session): start by reading the latest [`docs/dev_log/`](./docs/dev_log/) entry — it doubles as a sticky-decisions handoff.

<!-- --- -->

## License

MIT. See [LICENSE](./LICENSE).
