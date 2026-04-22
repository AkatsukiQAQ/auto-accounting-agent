# Backend Phase 1 — "Pipeline as a service"

**Scope:** rebuild the legacy three-tool pipeline as a real HTTP service with a
database underneath. Ship the API surface that `PHASE_1.md` (frontend) promises
to consume. Match the behavior of the legacy pipeline on real receipts while
giving up the LangChain / LangGraph agent-tool wrapper.

**Estimated effort:** 3–4 days.

**Prerequisite:** [`BACKEND_PHASE_0.md`](./BACKEND_PHASE_0.md) done — `backend/core/` exists and has tests.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md), [`PHASE_1.md`](./PHASE_1.md) (the frontend phase this backend powers — they define the same API contract, in two voices).

---

## What you build in Phase 1

A FastAPI service with:

- **Two tables**: `transactions` and `categories`. No accounts, no budgets, no users.
- **Five REST resource groups**: `/api/transactions`, `/api/categories`, `/api/import/photo`, `/api/settings`, and a health check.
- **A new pipeline orchestrator** (`ImportPipeline`) that replaces the LangGraph agent. Deterministic stages. Returns a draft transaction, not a side-effect.
- **One DB seeder** that writes the 9 default categories on first boot.
- **OpenAPI docs** at `/docs` — free with FastAPI, required for the frontend to dev against.

The pipeline runs on-demand inside the HTTP request (no queue, no worker). Phase 2 adds workers; Phase 1 stays boring.

---

## What you explicitly do NOT build in Phase 1

| Do not build | Why |
|---|---|
| `accounts` table / account_id on transactions | Phase 2. |
| Merchant normalization / `merchants` / `merchant_aliases` | Phase 2. |
| Transfers | Phase 2. |
| Budgets, recurring rules, review queue | Phase 2. |
| Classification rules learned from user corrections | Phase 3. |
| Authentication / multi-tenant | Out of scope. Single-user, hardcoded tenant ID. |
| A worker / cron / background queue | Not needed until Phase 2's recurring rules. |
| Observability beyond stdout logging | Add OpenTelemetry when you need it — you don't yet. |

---

## Architecture

Three layers, strict direction of imports (higher → lower only):

```
┌───────────────────────────────────────────────────────┐
│  api/          FastAPI routes. Thin. HTTP ↔ service.  │
├───────────────────────────────────────────────────────┤
│  services/     Orchestration, pipeline, biz logic.    │
│                Imports from core/ and db/.            │
├───────────────────────────────────────────────────────┤
│  db/           SQLAlchemy models, session, seeders.   │
│  core/         Pure functions (Phase 0 output).       │
└───────────────────────────────────────────────────────┘
```

`api/` never imports from `db/` directly. `core/` never imports from anything above it. Services are where orchestration lives.

### Project structure after Phase 1

```
backend/
├── api/                              # NEW
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory, CORS, error handlers
│   ├── deps.py                       # Dependency providers (get_session, get_pipeline)
│   ├── errors.py                     # HTTPException subclasses, exception_handler
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── transactions.py
│   │   ├── categories.py
│   │   ├── imports.py                # POST /api/import/photo
│   │   ├── settings.py
│   │   └── health.py
│   └── schemas/                      # Pydantic request/response DTOs (distinct from core/schemas)
│       ├── __init__.py
│       ├── transaction.py
│       ├── category.py
│       ├── import_.py
│       └── settings.py
│
├── services/                         # NEW
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # ImportPipeline — replaces create_react_agent
│   │   ├── stages.py                 # OCRStage, ParseStage, ClassifyStage
│   │   ├── llm.py                    # PipelineLLM interface + OpenAIPipelineLLM impl
│   │   └── result.py                 # PipelineResult dataclass
│   ├── transactions.py               # create_transaction, update_transaction, delete_transaction
│   ├── categories.py                 # CRUD + guardrails (e.g. can't delete if referenced)
│   └── settings.py                   # get_settings, update_settings
│
├── db/                               # NEW
│   ├── __init__.py
│   ├── base.py                       # DeclarativeBase, naming conventions
│   ├── session.py                    # engine, SessionLocal, get_session()
│   ├── models/
│   │   ├── __init__.py
│   │   ├── transaction.py
│   │   ├── category.py
│   │   └── settings.py
│   ├── seeders/
│   │   ├── __init__.py
│   │   └── categories.py             # reads core.categories_seed, writes DB
│   └── migrations/                   # Alembic
│       ├── env.py
│       └── versions/
│           └── 0001_initial.py
│
├── core/                             # From Phase 0 — unchanged
├── configs/                          # From Phase 0 — unchanged
├── tools/                            # LEGACY — delete at the end of Phase 1
│
├── tests/
│   ├── core/                         # From Phase 0
│   ├── services/
│   │   └── test_pipeline.py          # Integration: fake LLM, real image
│   └── api/
│       ├── test_transactions.py      # TestClient against in-memory SQLite
│       ├── test_import.py
│       └── test_categories.py
│
├── pyproject.toml                    # NEW — replaces loose requirements.txt
├── alembic.ini                       # NEW
├── .env.example                      # DATABASE_URL, OPENAI_API_KEY, IMAGE_STORAGE_DIR
└── README.md                         # Updated
```

---

## Data model — Phase 1

Mirror `PHASE_1.md` exactly. For completeness, repeated here in SQLAlchemy terms.

```python
# db/models/category.py
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[str] = mapped_column(String, primary_key=True)           # slug
    label: Mapped[str] = mapped_column(String, nullable=False)
    color_bg: Mapped[str] = mapped_column(String, nullable=False)
    color_dot: Mapped[str] = mapped_column(String, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    auto_assign: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# db/models/transaction.py
class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True)           # uuid
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    source: Mapped[Literal["photo","manual"]] = mapped_column(String, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ocr_engine: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_llm_model: Mapped[str | None] = mapped_column(String, nullable=True)

# db/models/settings.py
class UserSettings(Base):
    __tablename__ = "user_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)  # single row
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # Settings shape as JSON
```

Single-row `user_settings` with `id=1` is a fine Phase 1 simplification. If you're using Postgres, consider adding a `CHECK (id = 1)` constraint to enforce it.

### Amount sign convention

`amount_cents` is signed. Negative = expense, positive = income. No `type` column in Phase 1 — the sign carries that. Phase 2 adds `type` for transfers; until then, don't let it creep in.

### Currency per row

Each transaction carries its own currency. The legacy `CurrencyParser` already detects from the receipt. Don't normalize on write. The frontend decides how to display mixed currencies (Phase 1 shows each transaction in its own currency).

### Seeder

`db/seeders/categories.py` calls `core.categories_seed.load_seed_categories()` (Phase 0 output) and upserts. Run on first boot only — check `SELECT count(*) FROM categories` first.

Seed data: the 9 categories from `CAT_COLORS` in the frontend's `primitives.jsx` — Food, Transport, Shopping, Bills, Entertain, Health, Income, Rent, Other. Colors come from the frontend palette (see `PHASE_1.md` → Data model → categories). The legacy `CategoryConfigs.yaml` has ~9 similar categories but different names (Supermarket / Convenience Store / Transportation / Restaurant / Delivery / Shopping / Game / Health / Sports / Others) — **use the frontend's list, not the YAML's**. The keywords can still be seeded from the YAML where they overlap; map legacy names to new slugs in `core/categories_seed.py`:

| Legacy YAML name | Phase 1 slug | Label |
|---|---|---|
| Supermarket + Convenience Store | `food` | Food |
| Restaurant + Delivery | `food` | (merged) |
| Transportation | `transport` | Transport |
| Shopping | `shopping` | Shopping |
| — | `bills` | Bills (no seed keywords) |
| Game + Sports | `entertain` | Entertain |
| Health | `health` | Health |
| — | `income` | Income (no seed keywords) |
| — | `rent` | Rent (no seed keywords) |
| Others | `other` | Other |

Keywords merge into the destination slug's `keywords` array.

---

## The new pipeline

### Interface

```python
# services/pipeline/llm.py
from typing import Protocol

class PipelineLLM(Protocol):
    def complete_structured(self, prompt: str, schema: type[BaseModel], images: list[str] | None = None) -> BaseModel: ...
    @property
    def model_name(self) -> str: ...

class OpenAIPipelineLLM:
    """Concrete impl. Wraps openai SDK directly — no langchain."""
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = OpenAI(api_key=api_key)
        self._model = model
    def complete_structured(self, prompt, schema, images=None):
        # uses client.responses.parse with response_format=schema
        ...
```

`PipelineLLM` is the whole LLM abstraction. No LangChain tools, no LangGraph, no `@tool` decorators. Tests use `FakePipelineLLM` that returns canned `BaseModel` instances.

### Stages

Each stage is a callable class with one method. Stages take the DB session + LLM + previous-stage output, and produce the next-stage output. No global state.

```python
# services/pipeline/stages.py
@dataclass
class StageContext:
    llm: PipelineLLM
    session: Session
    config: PipelineConfig  # accepted currencies, symbol defaults, etc.

class OCRStage:
    """Image bytes → OCR_Results (list of receipt raw_text blocks)."""
    def run(self, ctx: StageContext, image_path: str) -> OCR_Results:
        prompt = render_ocr_prompt()
        return ctx.llm.complete_structured(prompt, OCR_Results, images=[image_path])

class ParseStage:
    """OCR_Results → ParsedOcrResult (currency, amount, date, merchant extracted)."""
    def run(self, ctx: StageContext, ocr: OCR_Results) -> ParsedOcrResult:
        # Normalize text using core.currency.normalize_text
        # Render prompt with core.prompts.render_parser_prompt
        # Call LLM, validate output
        # Post-process: drop rows whose currency isn't in accepted list
        ...

class ClassifyStage:
    """ParsedOcrResult → ClassificationResult. Regex first, LLM for fallbacks."""
    def run(self, ctx: StageContext, parsed: ParsedOcrResult) -> ClassificationResult:
        categories = ctx.session.scalars(select(CategoryModel)).all()
        category_objs = [hydrate_category(c) for c in categories]  # core.Category with compiled regex
        buckets = regex_classify_batch(parsed, category_objs)      # Phase 0 function
        llm_results = self._llm_classify_remainders(ctx, buckets)
        return merge(buckets.matched, llm_results)
```

Note: `ClassifyStage` reads categories from the DB (they're user-editable now), not from the YAML (which only seeds first boot).

### Orchestrator

```python
# services/pipeline/orchestrator.py
class ImportPipeline:
    def __init__(self, ocr: OCRStage, parse: ParseStage, classify: ClassifyStage):
        self.ocr, self.parse, self.classify = ocr, parse, classify

    def run(self, ctx: StageContext, image_path: str) -> PipelineResult:
        t0 = time.monotonic()
        ocr_result = self.ocr.run(ctx, image_path)
        parsed = self.parse.run(ctx, ocr_result)
        classified = self.classify.run(ctx, parsed)
        return PipelineResult(
            ocr=ocr_result,
            parsed=parsed,
            classified=classified,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
            llm_model=ctx.llm.model_name,
        )
```

That's the whole "agent". Three method calls, one return value. No framework. Easy to test (inject `FakePipelineLLM`, assert on `PipelineResult`). Phase 3's "pipeline visualization" feature (A2 in `PHASE_3.md`) comes for free because each stage's output is already preserved on `PipelineResult`.

### Why not keep LangGraph?

Legacy uses `create_react_agent` with three tools. The agent *decides* the order to call them, which means:

- **Non-determinism.** Two runs on the same image can produce different tool-call sequences. Fine for chat agents; not fine for a pipeline.
- **Wasted tokens.** Each tool call round-trips through the LLM to decide the next move. For a fixed OCR → parse → classify chain, that's pure overhead.
- **Hard to test.** You can't call "just the parser" in isolation without the agent loop.
- **Hard to expose stages to the UI.** Pipeline visualization (Phase 3 A2) wants "here's what OCR said, here's what parser did with it, here's what classifier decided" — the agent abstracts all of that away.

Keep LangGraph in your toolbox for agentic features (the chatbot in Phase 3 B1 might use it). For deterministic pipelines, use a plain class.

---

## API contract

All endpoints: JSON in / out, responses wrapped as `{ "data": T }` for success and `{ "error": { "code": str, "message": str } }` for failure. Frontend's `PHASE_1.md` §"API contract" is the source of truth; this section adds backend-specific implementation notes.

### `POST /api/import/photo`

Request: `multipart/form-data` with one `image` file.

Response:

```json
{
  "data": {
    "previewTransaction": {
      "occurredAt": "2026-04-21T12:34:00+09:00",
      "merchant": "Starbucks",
      "amountCents": -725,
      "currency": "JPY",
      "categoryId": "food",
      "source": "photo",
      "confidence": 0.82,
      "note": null,
      "raw": {
        "imageUrl": "/media/2026/04/abc123.jpg",
        "ocrText": "STARBUCKS ...",
        "ocrEngine": "gpt-4o-mini",
        "llmModel": "gpt-4o-mini"
      }
    },
    "confidence": 0.82,
    "ocrText": "STARBUCKS ...",
    "ocrEngine": "gpt-4o-mini",
    "llmModel": "gpt-4o-mini"
  }
}
```

Implementation:

1. Save the uploaded image to `$IMAGE_STORAGE_DIR/{YYYY}/{MM}/{uuid}.{ext}`. For local dev, filesystem is fine; for prod, swap to S3/R2 later. The path that becomes `raw.imageUrl` is served by a `/media` static mount in Phase 1 (good enough).
2. Run `ImportPipeline.run(ctx, saved_path)`.
3. Pick the first receipt from the result (the legacy pipeline handles multi-receipt images, but Phase 1's frontend assumes one-per-upload — drop the rest for now; log a warning).
4. Build a `TransactionInput` from the pipeline result. If `ClassificationResult.matched=False`, default `categoryId='other'`.
5. Compute overall confidence. Simple approach for Phase 1: `0.5 * parse_confidence + 0.5 * classify_confidence`, where:
   - `parse_confidence` = 1.0 if currency + amount + date all non-null, 0.7 if amount + currency present, 0.3 otherwise.
   - `classify_confidence` = 1.0 if regex-matched, 0.75 if LLM-matched with a keyword, 0.4 if LLM-fallback-to-Other.
6. Return the draft. **Do not write to `transactions`.** The frontend posts the user-edited version to `POST /api/transactions`.

This matches `PHASE_1.md`'s "two-step flow" requirement.

### `GET /api/transactions`

Query params (all optional):

- `from`, `to` — ISO dates, applied to `occurred_at`
- `category` — comma-separated category ids
- `q` — substring match on `merchant` (case-insensitive); Phase 2 adds `merchant_raw`
- `limit` — default 50, max 200
- `cursor` — opaque base64-encoded `{occurredAt, id}` for pagination

Sort: `occurred_at DESC, id DESC`. Stable for pagination.

Return shape: `{ data: Transaction[], nextCursor: str | null }`.

### `POST /api/transactions`

Body: `TransactionInput`. Validate:

- `categoryId` exists in `categories`, else 400
- `currency` is a 3-letter ISO code (regex `^[A-Z]{3}$`), else 400
- `amountCents` is a signed integer (non-zero, else 400)
- `occurredAt` parses as ISO 8601

Generate `id` server-side (UUIDv4 → `"txn_" + base62(uuid)`). Return 201 with `{ data: Transaction }`.

### `PATCH /api/transactions/:id`

Body: partial `TransactionInput`. Same validations for fields that are present. Return `{ data: Transaction }`. 404 if not found.

### `DELETE /api/transactions/:id`

Return `{ data: { ok: true } }`. 404 if not found. No cascade concerns yet (Phase 2 introduces balances).

### `GET/POST/PATCH/DELETE /api/categories`

Straightforward CRUD. The only subtlety: **`DELETE /api/categories/:id` must 409 if any transaction references the category.** Body of the 409: `{ error: { code: "category_in_use", message: "...", meta: { transactionCount: N } } }`. Suggest to the user (in frontend) that they bulk-reassign first.

Seed category `other` is undeletable — return 409 with `code: "cannot_delete_system_category"`.

### `GET /api/settings`, `PATCH /api/settings`

Returns the `Settings` JSON from `user_settings` row 1. On PATCH, deep-merge the request body with the stored value. Missing fields keep their old values; explicit `null` clears.

### `GET /api/health`

`{ data: { ok: true, version: "0.1.0" } }`. Used by deployment health checks.

---

## Error handling

Four error codes in Phase 1:

| HTTP | code | When |
|---|---|---|
| 400 | `validation_error` | Pydantic validation failed on the request body. `meta.fieldErrors` has the details. |
| 404 | `not_found` | Resource doesn't exist. |
| 409 | `conflict` | Category-in-use, system-category-delete, unique violation. `code` further specifies (`category_in_use`, `cannot_delete_system_category`). |
| 500 | `internal_error` | Anything else. Log the traceback; return a generic message. |

Pipeline failures during `POST /api/import/photo` deserve their own handling:

- OCR returns nothing → 200 with `confidence: 0.0` and a placeholder draft (`merchant: "Unknown"`, `amountCents: 0`, `categoryId: "other"`) so the user can manually fill in. Don't 500 on empty OCR.
- LLM call raises → 502 with `code: "pipeline_llm_error"`. Frontend shows a retry button.
- Invalid image format → 400 with `code: "unsupported_image"`.

---

## Config

`.env` file, loaded via `pydantic-settings`:

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///./mita.db"
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    image_storage_dir: str = "./storage/images"
    image_public_base_url: str = "/media"
    accepted_currencies: list[str] = ["USD","JPY","CNY","HKD","EUR","GBP","KRW"]
    cors_origins: list[str] = ["http://localhost:5173"]
    class Config:
        env_file = ".env"
```

Do **not** hardcode model names anywhere in code. `llm_model` is the single source of truth.

---

## Testing

Three layers, matching the architecture:

### `tests/core/*` — Phase 0 output

Already passing. Don't regress.

### `tests/services/test_pipeline.py` — pipeline integration with fake LLM

```python
def test_pipeline_end_to_end(session, fake_llm_factory):
    fake_llm = fake_llm_factory({
        OCR_Results: OCR_Results(ocr_results=[OCR_Receipt(raw_text="STARBUCKS ¥725")]),
        ParsedOcrResult: ParsedOcrResult(parsed_ocr_results=[
            ParsedReceipt(raw_text="STARBUCKS ¥725", currency="JPY", amount=725, date=None, time=None, merchant="Starbucks")
        ]),
        ClassificationResult: ClassificationResult(classification_results=[
            ReceiptClassification(idx=0, category="food", sub_category=None, matched=True, keyword="starbucks")
        ]),
    })
    pipeline = build_pipeline(fake_llm)
    result = pipeline.run(StageContext(llm=fake_llm, session=session, config=TEST_CFG), "tests/fixtures/starbucks.jpg")
    assert result.classified.classification_results[0].category == "food"
    assert result.parsed.parsed_ocr_results[0].currency == "JPY"
```

### `tests/api/*` — FastAPI TestClient against in-memory SQLite

One test per endpoint at minimum. Integration-style, not unit. Uses `httpx.AsyncClient` or FastAPI's `TestClient`. Override `get_session` and `get_pipeline` dependencies with test fixtures.

### End-to-end smoke test

One test that hits `POST /api/import/photo` with a real image fixture, using `FakePipelineLLM`, then hits `POST /api/transactions` with the returned draft, then `GET /api/transactions` and asserts the row is there.

---

## Migration from legacy

Phase 1 deletes `backend/tools/` at the end. Before that:

1. Stand up the new FastAPI service in parallel. Both codepaths import from `backend/core/`.
2. Pick 5–10 test receipts. Run each through the legacy `test.py` flow and through `POST /api/import/photo`. Diff the outputs — categories should match, amounts should match, currencies should match.
3. If there's drift, figure out which side is right. Usually the new side is right (Phase 0 fixed the latent bugs — see `BACKEND_PHASE_0.md` §"Fixes to make while you're in there"). Update any tests/fixtures.
4. Once parity is confirmed, delete `backend/tools/` and remove any `from langchain...` / `from langgraph...` imports from the codebase entirely.
5. `requirements.txt` → `pyproject.toml`: **drop all LangChain-family packages** — `langchain`, `langchain-openai`, `langchain-core`, `langchain-text-splitters`, `langgraph*`, `langsmith`. LangChain is not used in Phase 1 or Phase 2; it comes back only in Phase 3 B1 (chatbot orchestrator). Add `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `pydantic-settings`, `openai` (standalone SDK), `python-multipart`.

---

## Checklist before calling Phase 1 done

- [ ] `uvicorn backend.api.main:app --reload` starts cleanly on a fresh checkout after `alembic upgrade head`.
- [ ] `/docs` shows all 5 resource groups with request/response schemas.
- [ ] `curl POST /api/import/photo -F image=@receipt.jpg` returns a draft transaction without 500ing.
- [ ] `curl POST /api/transactions` with the draft creates a row; `GET /api/transactions` returns it.
- [ ] Deleting a category that's in use returns 409, not 500.
- [ ] `pytest` passes with ≥30 tests across core / services / api.
- [ ] No `langchain*` or `langgraph*` imports anywhere in the codebase. The `openai` SDK alone handles all Phase 1 LLM work (structured output via `client.responses.parse`, retries via `max_retries`).
- [ ] The frontend's Phase 1 app can run end-to-end against this backend with CORS enabled.
- [ ] Legacy `backend/tools/*.py` deleted. `test.py` removed.

---

## Stack decisions — already locked

These are settled. Do not re-litigate during implementation unless a concrete blocker shows up.

1. **Web framework — FastAPI.** Pydantic v2 is already a project dep; free OpenAPI docs at `/docs`; best-in-class for the request/response Pydantic schemas we've written.
2. **Database — SQLite.** Single file (`mita.db`), zero operational overhead, backup = copy. This is a single-user personal finance system; Postgres's concurrency/role/scale features don't apply. Enable WAL mode at startup (see "Local development workflow" below) so reads don't block writes.
   - **Why not Postgres:** no feature in Phase 1-2 needs it. JSONB → SQLite's JSON type is fine; ARRAY unused; no full-text search in scope; no cron triggers (we use an in-process worker); no pg_trgm (normalization is exact-match + rules).
   - **Migration path if you ever need to switch:** just change `DATABASE_URL=sqlite:///./mita.db` → `postgresql://...`. SQLAlchemy abstracts the differences. A few BigInteger/JSON default-value edge cases may surface; fix them when you see them. Don't pre-optimize for a migration that may never happen.
   - **Known SQLite caveats:** `ALTER TABLE` is limited (no DROP COLUMN before SQLite 3.35). Alembic's `batch_mode` handles this by rebuilding tables. Phase 2 migrations will be slightly more verbose as a result — acceptable.
3. **ORM — SQLAlchemy 2.0, sync.** Don't use async for Phase 1. A single-user service at <1 QPS doesn't need async DB access, and sync code is easier to reason about in a pipeline with image I/O and LLM calls already serialized. Revisit in Phase 2 only if the recurring worker actually causes contention.
4. **Migrations — Alembic.** `alembic init alembic`; commit `alembic/versions/`. Use `render_as_batch=True` in `env.py` so SQLite ALTER statements work.
5. **Image storage — local filesystem.** Mount `./storage/images` at `/media`. `image_public_base_url` env var is the S3/R2 swap seam for later.
6. **LLM SDK — standalone `openai` SDK.** No LangChain in Phase 1. Use `client.responses.parse(model=..., input=..., text_format=SomePydanticModel)` for structured output. Everything LangChain was giving us (structured output, retries) is now first-class in the OpenAPI SDK; LangChain just adds a dependency and an abstraction tax. **LangChain / LangGraph come back in Phase 3 B1 (chatbot)** — that's the only place actual agent orchestration is warranted. Phase 1-2 pipeline stages are deterministic functions, not agents.
7. **Deployment — localhost only for now.** No Docker, no cloud, no reverse proxy. Uvicorn on `localhost:8000`. Defer deployment decisions until the product is stable.

---

## Local development workflow

Because you expect to kill and restart the dev server constantly (during testing, when switching branches, when a stage raises and hangs), we need bulletproof port hygiene. Three layers:

### Layer 1 — `scripts/dev.sh` kills-before-starts

Create `scripts/dev.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-8000}"

# Kill any process still holding the port (works on macOS + Linux)
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "→ Port $PORT in use; killing stale process(es)..."
  lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.3
fi

exec uvicorn backend.api.main:app --reload --host 127.0.0.1 --port "$PORT"
```

Make it executable: `chmod +x scripts/dev.sh`.

### Layer 2 — `Makefile` for common ops

```makefile
.PHONY: dev stop restart db-migrate db-reset test

PORT ?= 8000

dev:
	@./scripts/dev.sh

stop:
	@lsof -ti:$(PORT) | xargs kill -9 2>/dev/null || echo "No process on :$(PORT)"

restart: stop dev

db-migrate:
	alembic upgrade head

db-reset:
	rm -f mita.db
	alembic upgrade head

test:
	pytest -x
```

Daily usage: `make dev` (auto-cleans port → starts), `make stop` (force-release port), `make db-reset` (wipe + remigrate — dev only).

### Layer 3 — FastAPI lifespan for graceful shutdown

In `backend/api/main.py`:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import event
from backend.api.db import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: enable WAL mode on SQLite for better read/write concurrency
    if engine.url.drivername.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    yield
    # Shutdown: release DB connections
    engine.dispose()

app = FastAPI(title="Mita API", lifespan=lifespan)
```

This handles clean `Ctrl+C`. `kill -9` bypasses it — that's what Layer 1 catches.

### Why all three layers?

- **Layer 1** = the default happy path. `make dev` always works.
- **Layer 2** = convenience + discoverability. New contributor runs `make` and sees the verbs.
- **Layer 3** = correctness when the process *does* get to shut down gracefully (SQLite connections need closing to flush WAL).

Together: you can `Ctrl+C`, `kill -9`, close the terminal, yank the power cord — next `make dev` always starts cleanly.
