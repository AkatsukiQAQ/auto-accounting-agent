# Backend Phase 4 — half-automated CSV sync

**Scope:** add a "drop a CSV file → it gets imported" pathway alongside the
Phase 1 photo-upload flow. The user keeps doing the bare minimum (export
CSV from their payment app, drop it in a watched folder OR forward a
statement email), and the backend handles parsing, dedup, classification,
and review-queue routing.

**Estimated effort:** 2–3 days.

**Prerequisite:**
- [`BACKEND_PHASE_2.md`](./BACKEND_PHASE_2.md) — `review_queue` table +
  `ReviewRouter` are reused here for low-confidence rows.
- [`BACKEND_PHASE_1.md`](./BACKEND_PHASE_1.md) — pipeline classification
  is reused; only the OCR + parse stages are skipped (CSV is already
  structured).

**Read alongside:** [`PHASE_4.md`](./PHASE_4.md) (frontend phase — UI is
intentionally deferred and designed during implementation).

---

## Why Phase 4 exists

Phase 1's photo-upload model is genuinely useful but high-friction for
daily use: snap → wait 60s for the LLM → confirm → save. For a user
who tracks 30+ transactions a month, that's ~30 minutes of dedicated
time.

PayPay, Alipay, WeChat Pay, Apple Card, and most banks ship a "Export
CSV" feature. The CSV is already structured — merchant, amount, date,
currency are pre-extracted by the source app. The backend doesn't need
to OCR; it just needs to parse + classify + dedup.

Result: drop one CSV → 30 transactions imported in ~5 seconds.

---

## What you build in Phase 4

A `services/sync/` module with:

- **A pluggable parser registry** (`PayPayCSVParser`, `AlipayCSVParser`,
  `WeChatPayCSVParser`, `GenericCSVParser` — more added as needed).
- **Source registry** (`sync_sources` table) — each row defines a way
  the backend can pull CSVs (folder watch + IMAP mailbox in v1).
- **A scheduler** (in-process, no external dep) that polls each source
  on a tick.
- **Dedup logic** that prevents re-importing the same transaction twice.
- **`POST /api/sync/run`** — manual trigger.
- **`GET /api/sync/status`** — last-run summary.
- **`GET/POST/PATCH/DELETE /api/sync/sources`** — CRUD over sources.

Imported rows feed the existing `ImportPipeline` skipping OCR + Parse
stages — only the `ClassifyStage` (regex-first, LLM-fallback) runs.
Phase 2's `ReviewRouter` decides: high-confidence → `transactions`,
low-confidence → `review_queue`.

---

## What you explicitly do NOT build in Phase 4

| Do not build | Why |
|---|---|
| Direct API integration with PayPay / Alipay | No public API for individual users. Out of scope (see Phase 2 §Bank sync). |
| Browser-automation scraping | Fragile, breaks weekly, ToS-risky. Half-automated CSV is the design. |
| Plaid / Yodlee / Money Forward third-party aggregators | None of these support the target apps for individual users; subscription cost. |
| Live webhook listeners | Out of scope; no upstream sends webhooks for personal accounts. |
| iOS Share Sheet integration | Requires native iOS app; out of scope for a web app. Phase 5+. |
| Encrypted CSV at rest | Source files are already on the user's machine. Don't double-encrypt; just delete after archiving. |

---

## Architecture

Build on top of Phase 2's pipeline. Adds one new horizontal slice:

```
┌────────────────────────────────────────────────────────────────┐
│  api/                                                          │
│    routes/sync.py — REST entry points                          │
├────────────────────────────────────────────────────────────────┤
│  services/                                                     │
│    sync/                                                       │
│      runner.py     — orchestrates one full sync run            │
│      sources.py    — Source CRUD                               │
│      watcher.py    — FolderWatcher (in-process)                │
│      mailer.py     — IMAPWatcher (Phase 4.5 if not v1)         │
│      parsers/      — per-format CSV parsers                    │
│      dedup.py      — duplicate detection                       │
│      archiver.py   — moves processed files                     │
│      scheduler.py  — wakes runners on a tick                   │
│    pipeline/       — Phase 1 ImportPipeline (reused)           │
├────────────────────────────────────────────────────────────────┤
│  db/models/        — new: SyncSource, ImportRun                │
└────────────────────────────────────────────────────────────────┘
```

The pipeline already supports a partial run (just classification) — add
a `ClassifyOnlyPipeline` factory that builds an `ImportPipeline` with
no-op OCR + Parse stages, OR just call `ClassifyStage.run` directly
from the sync runner. The latter is cleaner.

### Project structure delta after Phase 4

```
backend/
  services/
    sync/
      __init__.py
      runner.py
      sources.py
      watcher.py
      parsers/
        __init__.py        # registry: detect_format(path) → ParserClass
        base.py            # CSVParser Protocol
        paypay.py
        alipay.py
        wechat.py
        generic.py         # column-mapping driven
      dedup.py
      archiver.py
      scheduler.py
  db/
    models/
      sync_source.py       # new
      import_run.py        # new
    migrations/versions/
      0003_phase4_sync_sources_and_import_runs.py
  api/
    routes/sync.py
    schemas/sync.py
  tests/
    services/sync/
      test_parsers_paypay.py
      test_dedup.py
      test_runner.py
      fixtures/             # sample CSV files per format
        paypay_sample.csv
        alipay_sample.csv
        wechat_sample.csv
```

---

## Data model — Phase 4

### `sync_sources`

One row per "place the backend looks for new CSVs."

```python
class SyncSource(Base):
    __tablename__ = "sync_sources"
    id: Mapped[str] = mapped_column(String, primary_key=True)        # `src_<base62>`
    label: Mapped[str] = mapped_column(String, nullable=False)        # user-visible name
    kind: Mapped[Literal["folder", "imap"]] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)        # see below per kind
    parser_format: Mapped[str | None] = mapped_column(String, nullable=True)  # 'paypay' / 'alipay' / 'wechat' / 'generic'
    column_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # only for kind='generic'
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String, nullable=True)  # 'ok' / 'partial' / 'error'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**`config` shape per `kind`:**
- `kind='folder'`: `{"path": "/Users/yucheng/Downloads/PayPay", "archive_subdir": "processed"}`
- `kind='imap'`: `{"host": "imap.gmail.com", "port": 993, "username": "...", "password_ref": "imap_password_1", "search": "FROM:noreply@paypay.ne.jp HAS_ATTACHMENT"}` — `password_ref` points at a key in `user_settings.apiKeys` so the password isn't duplicated; the actual secret stays in the existing settings table.

**`parser_format`:** chosen at source creation. Heuristic auto-detect runs first; if ambiguous, frontend prompts for the format. Set to `'generic'` for unrecognized formats — then `column_mapping` is required.

**`column_mapping`:** for `parser_format='generic'`, e.g.
```json
{
  "occurred_at": {"column": "Date", "format": "%Y/%m/%d"},
  "merchant":    {"column": "Description"},
  "amount_cents":{"column": "Amount", "scale": 100, "sign": "as-is"},
  "currency":    {"column": "Currency", "default": "JPY"}
}
```
`scale` says "multiply value by 100 to get cents" (for `Amount` columns
expressed in major units). `sign: 'as-is' | 'flip'` lets the user
correct CSVs that report expenses as positive numbers.

### `import_runs`

Per-run audit log; useful for "why didn't my Sept import bring in row 7?"

```python
class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)        # `run_<base62>`
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sync_sources.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String, nullable=True)
    file_archived_to: Mapped[str | None] = mapped_column(String, nullable=True)
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Every CSV imported produces one `ImportRun` row. Manual `POST /api/sync/run`
without source_id (one-off file upload) also creates a row with
`source_id=NULL`.

### Extension to `transactions`

Add a column linking back to the import run that created each row:

```python
import_run_id: Mapped[str | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True, index=True)
```

Lets the user see "all transactions from this CSV." Phase 1's photo
imports leave it `NULL`. Phase 4's CSV imports populate it.

---

## Parser registry

Each parser implements:

```python
class CSVParser(Protocol):
    format_id: str   # 'paypay', 'alipay', 'wechat', 'generic', ...

    @classmethod
    def can_parse(cls, path: Path, sample_rows: list[dict]) -> bool:
        """Heuristic detection — column names, file name patterns, locale clues."""

    def parse(
        self,
        path: Path,
        column_mapping: dict | None = None,
    ) -> Iterator[ParsedRow]:
        """Yield one ParsedRow per CSV record. Skip empty/comment rows."""
```

`ParsedRow` is a small dataclass that mirrors `core.schemas.ParsedReceipt`
plus a `raw` dict carrying the original row for debugging:

```python
@dataclass
class ParsedRow:
    occurred_at: datetime
    merchant: str
    amount_cents: int      # signed (negative = expense)
    currency: str
    note: str | None
    raw: dict[str, str]    # original CSV columns
```

**Initial built-in parsers (v1):**
- `PayPayCSVParser` — Japanese app. Columns: `日付 / 取引内容 / 金額 / 通貨` (varies by version). Locale handling: Japanese date formats `2026年4月22日`, half-width / full-width digits.
- `AlipayCSVParser` — Chinese app. Columns: `交易时间 / 交易对方 / 金额 / 收/支`. The `收/支` column tells expense vs income; map to sign.
- `WeChatPayCSVParser` — same idea as Alipay; different column names.
- `GenericCSVParser` — driven by `column_mapping` from `sync_sources.column_mapping`. Used when no built-in matches.

**Detection order** (in `parsers/__init__.py::detect_format`):
1. Check filename for known prefixes (`paypay_*.csv`, `alipay_*.xlsx`).
2. Read first 20 rows; check column headers against each parser's `can_parse`.
3. First match wins. If none → `'generic'`, prompt the user to map columns.

---

## Sync runner

The orchestrator:

```python
def run_sync(source: SyncSource | None, file: Path | None) -> ImportRun:
    """One pass. Either driven by a registered source (folder/imap) or by an
    ad-hoc file upload (source=None, file=path)."""
    run = ImportRun.start(...)
    try:
        if source and source.kind == 'folder':
            files = scan_folder(source.config['path'])
        elif source and source.kind == 'imap':
            files = fetch_imap_attachments(source.config)
        else:
            files = [file]

        for path in files:
            parser = pick_parser(path, source)
            for row in parser.parse(path, source.column_mapping if source else None):
                if dedup.is_duplicate(row):
                    run.rows_duplicate += 1; continue
                classified = classify_row(row)        # reuses ClassifyStage
                draft = build_transaction_input(row, classified)
                if confidence(classified) >= REVIEW_THRESHOLD:
                    services.transactions.create(session, **draft, import_run_id=run.id)
                    run.rows_imported += 1
                else:
                    services.review_queue.enqueue(draft, reason='low_classify_confidence', import_run_id=run.id)
                    run.rows_review += 1
            archiver.archive(path, source.config.get('archive_subdir', 'processed'))
        run.finish(status='ok')
    except Exception as exc:
        run.finish(status='error', error_message=str(exc))
        raise
    return run
```

Key reuses from existing layers:
- `ClassifyStage._hydrate_categories_from_db` — load DB categories with compiled regex.
- `core.classifier.regex_classify_batch` — same regex-first logic as photo flow.
- `services.review_queue.enqueue` (Phase 2) — same routing rule as photo low-confidence.
- `core.currency.normalize_text` — clean merchant strings before regex.

---

## Dedup

`dedup.is_duplicate(row, session) → bool`:

A new row is a duplicate of an existing transaction iff **all** match:
1. Same `currency`.
2. Same `amount_cents` (exact int match).
3. `merchant_normalized` of new row == `merchant_normalized` of existing
   (use Phase 2's `NormalizationEngine`; compares "Starbucks Shibuya" vs
   "Starbucks").
4. `occurred_at` within ±2 days (configurable via env
   `DEDUP_DATE_WINDOW_DAYS`, default 2).

Rationale:
- Same payment may appear with slightly different timestamps when the
  CSV uses settlement date vs auth date.
- Merchant strings are noisy; raw equality misses obvious duplicates.

If multiple existing transactions match: skip the new row, log a
warning. Phase 4 doesn't try to merge metadata.

**False-positive guard:** if the user explicitly says "no, these are
two real visits," they can manually create a transaction in
`/records` even if dedup would have rejected it on import. The dedup
check only runs during sync, not during manual entry.

---

## Scheduler

In-process, no external dep. Simple background asyncio task started by
the FastAPI lifespan:

```python
async def sync_scheduler_loop(app):
    while True:
        await asyncio.sleep(SYNC_TICK_SECONDS)  # default 300 = 5 min
        for source in active_sources():
            try:
                run_sync(source, None)
            except Exception:
                logger.exception("sync_scheduler: source %s failed", source.id)
```

Lifespan starts the loop; cancels on shutdown. Single worker process is
fine for Phase 4 — Mita is single-user.

If concurrency becomes a problem (e.g. user manually triggers sync
during a scheduled run), use an `asyncio.Lock` per source — one lock per
source so different sources can run in parallel.

---

## API contract

All endpoints return the standard envelope (`{data: T}` for success,
`{error: {code, message, meta}}` for failure).

### `POST /api/sync/run`

Trigger a sync immediately. Two modes:
1. `{"sourceId": "src_abc"}` — run that source.
2. `multipart/form-data` with `file=<csv>` and optional `parserFormat`
   + `columnMapping` — one-off file. No source row needed.

Response: `Data[ImportRunSummary]` — the resulting run row.

### `GET /api/sync/runs`

List recent import runs, paginated. Shows source label, file name, row
counts, status. `?source=src_abc` filters to one source.

### `GET /api/sync/runs/:id`

Full detail: includes per-row results if you want to drill in (Phase 4
v1 just returns counts; v2 could log per-row outcomes).

### `GET/POST/PATCH/DELETE /api/sync/sources`

CRUD over `sync_sources`. Standard.

### `POST /api/sync/sources/:id/test`

Dry run: scan the source for new files, parse them, BUT don't write
anything to DB. Returns what *would* happen. Useful when adding a new
source to debug column mappings.

### Errors specific to sync

| HTTP | code | When |
|---|---|---|
| 400 | `unknown_csv_format` | No parser matched and no `column_mapping` provided. |
| 400 | `column_mapping_invalid` | Generic parser couldn't extract required fields. `meta.missingFields` lists them. |
| 400 | `source_disabled` | Tried to run a disabled source. |
| 404 | `not_found` | Unknown source id or run id. |
| 502 | `imap_connection_error` | IMAP source couldn't reach mail server. |
| 502 | `pipeline_llm_error` | If a row fell through to LLM classification and OpenAI failed (passthrough from Phase 1). |

---

## Testing

### Unit tests per parser

```
tests/services/sync/test_parsers_paypay.py
tests/services/sync/test_parsers_alipay.py
tests/services/sync/test_parsers_wechat.py
tests/services/sync/test_parsers_generic.py
```

Each loads a fixture CSV from `tests/services/sync/fixtures/` and asserts
`list(parser.parse(path))` produces the expected `ParsedRow`s. Fixtures
include:
- Happy-path sample (3–5 rows).
- Edge cases: empty rows, comment rows, missing optional columns,
  full-width digits, mixed currencies, expenses-as-positive (sign flip).

Each parser ≥ 5 tests.

### Dedup tests

```
test_dedup_exact_match
test_dedup_same_amount_different_currency
test_dedup_merchant_normalization_collapses_branches
test_dedup_date_window_2_days
test_dedup_outside_window_is_not_dup
test_dedup_skips_when_currency_differs
```

### Runner integration tests

Use FakePipelineLLM to control classification outcomes. Verify:
- Folder source picks up files in fixture dir.
- Files get archived after import.
- High-confidence rows go to transactions; low-confidence go to review_queue.
- Duplicates are counted in `rows_duplicate`, not imported.
- Errors during one row don't kill the whole run; counted in `rows_error`.

### API tests

Standard FastAPI TestClient suite in `tests/api/test_sync.py`. One test
per endpoint.

Target: ≥ 25 new tests across parsers + dedup + runner + API.

---

## Acceptance checklist

- [ ] `make test` passes; total tests ≥ Phase 3's count + 25.
- [ ] Drop a real PayPay CSV in the watched folder → within 5 minutes,
      transactions appear in `/records` (or in `/review` for
      low-confidence rows).
- [ ] Re-drop the same CSV → 0 new transactions, all reported as
      duplicate, file still archived.
- [ ] Add a Generic source with column mapping; drop a custom CSV →
      imports correctly.
- [ ] Click "Sync now" in the UI for an enabled source → the run
      appears in `GET /api/sync/runs` with rows counted.
- [ ] Disable a source → its scheduled tick is skipped; manual run on
      it returns 400 `source_disabled`.
- [ ] No PayPay/Alipay credentials in code or env (everything in
      `user_settings` or `sync_sources.config`).

---

## Open questions / deferred to Phase 4.5

- **IMAP source** — written in this design but might slip to a Phase
  4.5 if v1 ships without it. Folder watch is the primary path.
- **Per-row result log** in `import_runs` — v1 just keeps counts. If
  debugging gets painful, add a `ImportRunRow` table.
- **Scheduling jitter** — multiple sources at exactly :00 may stress
  the LLM rate limit. v1 doesn't stagger; revisit if it becomes a
  problem.
- **CSV format change detection** — if PayPay ships a new export
  format, parsers fail silently or noisily. Surface "format changed?"
  warnings in the UI.
