# Backend Phase 2 — "Ledger, cascades, workers"

**Scope:** take the Phase 1 service from a "photo-to-transaction tool" to an
actual personal-finance backend. Add accounts with real balances, budgets with
live spent/limit computation, recurring rules with a background worker,
transfers as paired transactions, merchant normalization, and a review queue
for low-confidence captures.

**Estimated effort:** ~1 week.

**Prerequisite:** [`BACKEND_PHASE_1.md`](./BACKEND_PHASE_1.md) deployed, running,
frontend Phase 1 consuming it happily.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md), [`PHASE_2.md`](./PHASE_2.md)
(the frontend phase this backend powers), `BACKEND_PHASE_1.md` (schema this
extends).

> **Start a fresh Claude Code session.** Phase 1 context carries assumptions
> from a two-table schema. Don't let it muddy Phase 2 cascade decisions.

---

## What you build in Phase 2

### New tables

- `accounts` — real balances, per-account transaction lists.
- `merchants` + `merchant_aliases` — brand normalization layer.
- `budgets` — per-category monthly (or weekly) caps.
- `recurring_rules` — subscription / bill templates that auto-generate transactions.
- `review_queue` — low-confidence captures pending human approval.

### Extensions to `transactions`

- `account_id` (required, backfilled).
- `type` enum: `normal | transfer_out | transfer_in | recurring`.
- `transfer_group_id` — links the two legs of a transfer.
- `recurring_rule_id` — set when auto-generated.
- `merchant_raw` + `merchant_normalized` — rename semantics of `merchant`.

### New services

- `ApplyTransactionService` — the single cascade function. Every mutation goes through it.
- `NormalizationService` — merchant_raw → merchant_normalized, rule-based first, LLM fallback.
- `RecurringWorker` — scheduled runner that fires due rules.
- `ReviewRouter` — decides at import time whether a draft goes to preview (Phase 1 flow) or to the review queue.

### New API surface

Matches `PHASE_2.md` §"API additions" verbatim. Enumerated in detail below.

---

## What you explicitly do NOT build in Phase 2

| Do not build | Why |
|---|---|
| Classification rules learned from user category edits | Phase 3 A1. |
| Pipeline stage visualization endpoints | Phase 3 A2. |
| Chatbot tool-access endpoints | Phase 3 B1. |
| Plaid / bank sync | Out of scope indefinitely. Accounts are manual-only. |
| CSV / statement import | Phase 3 C3. |
| Multi-user / tenant scoping | Still single-user. Hardcode tenant where needed. |

---

## Architecture updates

The layering from Phase 1 stays. Add one new concept:

```
┌───────────────────────────────────────────────────────┐
│  api/          FastAPI routes. Unchanged layering.    │
├───────────────────────────────────────────────────────┤
│  services/                                            │
│  ├── pipeline/       Now includes NormalizationStage  │
│  ├── ledger/         NEW — ApplyTransactionService,   │
│  │                   BudgetService, AccountService    │
│  ├── recurring/      NEW — RecurringWorker            │
│  └── review/         NEW — ReviewRouter               │
├───────────────────────────────────────────────────────┤
│  workers/            NEW — entry point for cron jobs  │
├───────────────────────────────────────────────────────┤
│  db/                 More models, more migrations     │
│  core/               Unchanged from Phase 0           │
└───────────────────────────────────────────────────────┘
```

### Project structure additions

```
backend/
├── api/routes/
│   ├── accounts.py                 # NEW
│   ├── transfers.py                # NEW
│   ├── budgets.py                  # NEW
│   ├── recurring.py                # NEW
│   ├── review.py                   # NEW
│   ├── merchants.py                # NEW
│   └── normalize.py                # NEW — POST /api/normalize (preview-only)
│
├── services/
│   ├── ledger/                     # NEW — the cascade home
│   │   ├── __init__.py
│   │   ├── apply.py                # ApplyTransactionService — single cascade entry point
│   │   ├── accounts.py             # balance recompute, reconcile
│   │   ├── budgets.py              # spent-cents-for-period compute
│   │   └── transfers.py            # create / update / delete paired rows
│   ├── pipeline/
│   │   └── stages.py               # adds NormalizationStage between Parse and Classify
│   ├── normalization/              # NEW
│   │   ├── __init__.py
│   │   ├── engine.py               # NormalizationEngine — aliases → strip → brand → fallback
│   │   ├── strippers.py            # Regex rules from PHASE_2.md
│   │   └── merchants_seed.py       # ~50 seed brands for target geography
│   ├── recurring/                  # NEW
│   │   ├── __init__.py
│   │   ├── worker.py               # RecurringWorker.run_due_rules(today)
│   │   └── cadence.py              # advance_next_run(cadence, day_of_month, ...)
│   └── review/                     # NEW
│       ├── __init__.py
│       ├── router.py               # ReviewRouter.route(pipeline_result) → preview | review
│       └── duplicates.py           # suspect-duplicate detection (48h window)
│
├── workers/                        # NEW — standalone entry points
│   ├── __init__.py
│   └── run_recurring.py            # python -m backend.workers.run_recurring
│
└── db/migrations/versions/
    ├── 0001_initial.py             # Phase 1
    ├── 0002_accounts.py            # NEW
    ├── 0003_transactions_extend.py # NEW — account_id, type, transfer_group, merchant_raw/normalized
    ├── 0004_merchants.py           # NEW
    ├── 0005_budgets.py             # NEW
    ├── 0006_recurring.py           # NEW
    └── 0007_review_queue.py        # NEW
```

---

## Data model

Defer to `PHASE_2.md` §"Data model additions" for the SQL DDL — it's the authoritative version. Below are the SQLAlchemy + implementation notes that don't belong in the frontend doc.

### `accounts`

```python
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # enum check constraint
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opening_balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    institution: Mapped[str | None]
    color: Mapped[str | None]
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**Materialization policy:** `balance_cents` is materialized — updated by the
cascade on every mutation. Do **not** compute it on read. Two reasons:

1. Dashboard net-worth queries happen on every page load; you don't want an `O(transactions)` aggregation each time.
2. Reconciliation (`POST /api/accounts/:id/reconcile`) writes a synthetic adjustment transaction and expects `balance_cents` to reflect it immediately.

The trade-off is drift risk if a mutation bypasses the cascade. Mitigate with:

- **Every write goes through `ApplyTransactionService`.** No route handler writes to `transactions` directly.
- A `POST /api/accounts/:id/recompute-balance` admin endpoint (not in `PHASE_2.md` — add it just for ops). Full recompute from `opening_balance_cents + SUM(transactions.amount_cents WHERE account_id = this AND type IN ('normal','transfer_out','transfer_in','recurring'))`.
- A Phase-2-done smoke test that creates 20 transactions (mix of normal + transfers + recurring), runs recompute, asserts delta is 0.

### `transactions` — extension

Alembic migration `0003_transactions_extend.py`:

```python
def upgrade():
    # 1. Add columns, all nullable or defaulted
    op.add_column("transactions", sa.Column("account_id", sa.String, sa.ForeignKey("accounts.id"), nullable=True))
    op.add_column("transactions", sa.Column("type", sa.String, nullable=False, server_default="normal"))
    op.add_column("transactions", sa.Column("transfer_group_id", sa.String, nullable=True))
    op.add_column("transactions", sa.Column("recurring_rule_id", sa.String, nullable=True))
    op.add_column("transactions", sa.Column("merchant_raw", sa.Text, nullable=True))
    op.add_column("transactions", sa.Column("merchant_normalized", sa.Text, nullable=True))
    op.create_check_constraint("transactions_type_check", "transactions",
        "type IN ('normal','transfer_out','transfer_in','recurring')")

    # 2. Data migration: create default "Cash" account, backfill account_id
    conn = op.get_bind()
    cash_id = "acc_cash_default"
    conn.execute(text("""
        INSERT INTO accounts (id, name, kind, currency, balance_cents, opening_balance_cents, created_at)
        VALUES (:id, 'Cash', 'cash', :ccy, 0, 0, now())
    """), {"id": cash_id, "ccy": DEFAULT_CURRENCY})
    conn.execute(text("UPDATE transactions SET account_id = :id WHERE account_id IS NULL"), {"id": cash_id})
    conn.execute(text("UPDATE transactions SET merchant_raw = merchant WHERE merchant_raw IS NULL"))
    conn.execute(text("UPDATE transactions SET merchant_normalized = merchant WHERE merchant_normalized IS NULL"))
    # Recompute Cash balance now that it has transactions pointing at it
    conn.execute(text("""
        UPDATE accounts SET balance_cents = opening_balance_cents + COALESCE((
          SELECT SUM(amount_cents) FROM transactions WHERE account_id = accounts.id
        ), 0) WHERE id = :id
    """), {"id": cash_id})

    # 3. Tighten: make account_id NOT NULL
    op.alter_column("transactions", "account_id", nullable=False)
```

Downgrade drops the columns but **does not** restore pre-Phase-1 state (deleting the default Cash account is destructive if the user has used Phase 2 for any time). Document this in the migration docstring.

**Semantics flip:** from Phase 2 on, `merchant` column is a compatibility alias — the application reads `merchant_normalized` everywhere. In the API response, send both as separate fields. In a future migration, drop `merchant` entirely; for Phase 2, keep it populated (= normalized) for rollback safety.

### `merchants` + `merchant_aliases`

See `PHASE_2.md` for the full DDL. Implementation note: `aliases` is JSONB in Postgres, JSON in SQLite. SQLAlchemy's `JSON` type handles both. Index the canonical_name and run a trigram-index (`pg_trgm`) on `aliases` for substring search if you're on Postgres and have >1000 merchants.

Seed data lives in `services/normalization/merchants_seed.py`. Start with ~50 brands relevant to your usage geography. JP: Family Mart, Lawson, 7-Eleven, Seibu, Don Quijote, Uniqlo, Muji, Uber Eats, Demae-can, JR (rail), Suica, Pasmo. CN: 美团, 饿了么, 淘宝, 京东, 星巴克, 麦当劳, 肯德基, 支付宝, 微信支付. Global: Amazon, Apple, Google, Netflix, Spotify, Steam.

Seed on first boot or via a one-off migration. Re-seeding after launch is a user-visible change (canonical names may differ); make it idempotent.

### `budgets`

Key decision: **don't materialize `spent_cents`.** Compute it on read.

```python
def compute_spent_cents(session, budget: Budget, today: date = None) -> int:
    period_start, period_end = period_bounds(budget.period, budget.starts_on, today or date.today())
    stmt = select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
        Transaction.category_id == budget.category_id,
        Transaction.occurred_at >= period_start,
        Transaction.occurred_at < period_end,
        Transaction.type.in_(("normal", "recurring")),  # exclude transfers
        Transaction.amount_cents < 0,                    # only expenses count
    )
    return -session.scalar(stmt)  # return positive cents spent
```

Why not materialize:

- Category edits on a transaction would require budget re-aggregation; error-prone.
- Period rollover adds another state machine.
- With a category index, the query is cheap (ms at personal-finance scale).

Materialize only if `GET /api/budgets` latency is actually a problem. It won't be.

**`rollover` behavior:** if `rollover = true` and the previous period's spent < limit, the unused amount is added to the current period's limit. Compute `effective_limit` recursively:

```python
def effective_limit_cents(session, budget: Budget, today: date) -> int:
    if not budget.rollover:
        return budget.limit_cents
    prev_start, prev_end = previous_period(budget.period, today)
    if prev_end <= budget.starts_on:
        return budget.limit_cents
    prev_spent = compute_spent_cents_in_window(session, budget, prev_start, prev_end)
    prev_effective = effective_limit_cents_at(session, budget, prev_start)  # recurse
    carried = max(0, prev_effective - prev_spent)
    return budget.limit_cents + carried
```

Cap the recursion depth at 12 periods. Nobody rolls over a year of budget.

### `recurring_rules`

Storing next run as a DATE instead of computing it from cadence: trades one redundant column for deterministic cron behavior (no timezone math on every read). Update `next_run_on` at the end of each run via `advance_next_run`:

```python
def advance_next_run(rule: RecurringRule, from_date: date) -> date:
    match rule.cadence:
        case "monthly":
            return next_month_day(from_date, rule.day_of_month)  # clamp 31 → last day
        case "weekly":
            return next_weekday(from_date, rule.day_of_week)
        case "yearly":
            return from_date.replace(year=from_date.year + 1)    # handle Feb 29
        case "custom":
            raise NotImplementedError("custom cadence Phase 3")
```

### `review_queue`

`draft` is a JSON blob of `TransactionInput` (not a FK-referenced row), because the draft may not be valid yet (missing category, etc.). When approved, validate and upsert into `transactions`; when rejected, just delete.

---

## `ApplyTransactionService` — the cascade contract

Single entry point for all transaction mutations. Every route handler calls it. DB triggers are the alternative; prefer a service for easier debugging in a 1-person project (per `PHASE_2.md` §"Stack questions").

### Interface

```python
class ApplyTransactionService:
    def create(self, session, input: TransactionInput, *, skip_duplicate_check: bool = False) -> Transaction | ReviewItem: ...
    def update(self, session, id: str, patch: dict) -> Transaction: ...
    def delete(self, session, id: str) -> None: ...
```

### On `create`:

1. **Validate FKs.** `account_id` exists and not archived; `category_id` exists.
2. **Normalize merchant** if not already populated. Run `NormalizationEngine.normalize(input.merchant_raw or input.merchant)` → writes both `merchant_raw` and `merchant_normalized`.
3. **Duplicate check** (unless `skip_duplicate_check=True`): if another transaction in the last 48h has the same `merchant_normalized`, `amount_cents`, and `account_id`, route to `review_queue` with `reason="duplicate_suspect"` and return the `ReviewItem` instead of creating. Caller is responsible for surfacing this to the user.
4. **Insert the row.**
5. **Bump account balance.** `accounts.balance_cents += input.amount_cents` WHERE id = `account_id`, inside the same DB transaction.
6. Commit. Return the new `Transaction`.

### On `update`:

Diff the patch against the existing row. Four cases matter:

- `amount_cents` changed → reverse old effect on old account, apply new effect on (possibly new) account.
- `account_id` changed but `amount_cents` same → reverse on old account, apply on new.
- `category_id` changed → no balance effect; budgets re-read will pick it up.
- `merchant_raw` changed → re-run normalization.

All of the above happens in a single DB transaction. If it gets hairy, simplify by internally doing `delete + create` (but careful with the `id` — keep it stable).

### On `delete`:

Reverse `amount_cents` on the account, delete the row. For transfers (`type IN ('transfer_out', 'transfer_in')`), delete **both legs** atomically via `transfer_group_id`.

### Transfers are a special case

Transfers are not created via `ApplyTransactionService.create`. They have their own service:

```python
class TransferService:
    def create(self, session, *, from_account_id: str, to_account_id: str, amount_cents: int, occurred_at: datetime, note: str | None) -> TransferPair:
        group_id = new_id("xfr")
        out_row = apply.create(session, TransactionInput(
            account_id=from_account_id, type="transfer_out", transfer_group_id=group_id,
            amount_cents=-abs(amount_cents), merchant=f"Transfer to {to_account.name}",
            category_id="transfer", ...), skip_duplicate_check=True)
        in_row = apply.create(session, TransactionInput(
            account_id=to_account_id, type="transfer_in", transfer_group_id=group_id,
            amount_cents=+abs(amount_cents), merchant=f"Transfer from {from_account.name}",
            category_id="transfer", ...), skip_duplicate_check=True)
        return TransferPair(out_row, in_row, group_id)
```

Add a seeded `transfer` category (system, undeletable) in Phase 2's first migration.

**Editing transfers:** edit both legs together; expose only via the transfer-specific endpoints, not `PATCH /api/transactions/:id`. If a user tries to PATCH one leg of a transfer via the generic endpoint, return 400 with `code: "transfer_leg_edit_forbidden"` pointing them to the transfer editor.

---

## Merchant normalization

A new pipeline stage inserted between `ParseStage` and `ClassifyStage` (see `BACKEND_PHASE_1.md` pipeline). The stage runs `NormalizationEngine.normalize(parsed.merchant)` for each parsed receipt, writing both `merchant_raw` (verbatim from OCR) and `merchant_normalized`.

### Strategy (from `PHASE_2.md`)

Try in order; first match wins.

1. **User aliases.** Query `merchant_aliases`. Match by `match_type`: `exact`, `contains`, or `regex`. If hit, return the linked merchant.
2. **Strip location / store suffixes.** Regex rules:
   - `\s*[（(].*[店号铺馆厅)）]\s*$` — CJK suffixed parentheses
   - `\s*\S+?店\s*$`, `\s*\S+?分店\s*$` — CJK "branch"
   - `\s*#?\d{2,}\s*$`, `\s*No\.?\s*\d+\s*$` — store numbers
   - `\s*[-–—]\s*.+?\s*(branch|store|outlet|location)\s*$` (case-insensitive)
   - `\s*\(.+?\)\s*$` — generic trailing parens, **skip if removing leaves <3 chars**
3. **Brand table lookup.** Search `merchants.aliases` JSON array for an exact match against the stripped name (normalized: lowercase, no whitespace).
4. **Fallback.** Use the stripped name. Title-case if it's all-caps. Track the raw in `merchant_raw`.

### Learning path

The `promote-to-merchant` rule from `PHASE_2.md`: if the fallback path fires with the same stripped name in ≥3 transactions, promote it to a `merchants` row with `source='learned'`. Background job; don't do it in the hot path.

Run this from the recurring worker daily (see below) — one more task on the same schedule. SQL:

```sql
WITH fallback_merchants AS (
  SELECT merchant_normalized, COUNT(*) as c
  FROM transactions
  WHERE merchant_normalized NOT IN (SELECT canonical_name FROM merchants)
    AND merchant_normalized NOT IN (SELECT canonical_name FROM merchants, jsonb_array_elements_text(aliases))
  GROUP BY merchant_normalized
  HAVING COUNT(*) >= 3
)
INSERT INTO merchants (id, canonical_name, aliases, source)
SELECT slug(name), name, '[]'::jsonb, 'learned'
FROM fallback_merchants;
```

---

## Recurring worker

### Interface

```python
class RecurringWorker:
    def __init__(self, session_factory, apply_svc: ApplyTransactionService):
        ...
    def run_due_rules(self, today: date | None = None) -> RecurringRunReport:
        """Find all rules where paused=false AND next_run_on <= today. Fire each.
        Idempotent: re-running on the same day with no new due rules is a no-op."""
```

### Firing a rule

1. Build `TransactionInput` from the rule's fields (merchant, amount, currency, category, account).
2. Set `type = "recurring"`, `recurring_rule_id = rule.id`.
3. Call `apply.create(...)` with `skip_duplicate_check=True` (recurring may legitimately repeat with same merchant + amount).
4. Update the rule: `last_run_on = today`, `next_run_on = advance_next_run(rule, today)`.

If `today - next_run_on > 30 days` (rule was paused and now unpaused, or worker was down), fire **once** and advance once. Do not backfill a year of rent. Optionally surface a warning to the user that the rule was stale.

### Entry point

`backend/workers/run_recurring.py`:

```python
if __name__ == "__main__":
    with session_factory() as s:
        worker = RecurringWorker(session_factory, apply_svc)
        report = worker.run_due_rules()
        print(json.dumps(report.dict(), default=str))
```

### Scheduling

The backend itself doesn't schedule. You configure a cron or hosted trigger in your deployment:

- **Fly.io** — `[[processes]] cron = "..."`
- **Railway / Render** — Cron Job resource
- **Supabase** — `pg_cron` pointing at an edge function that curls an authenticated endpoint
- **Local dev** — just run `python -m backend.workers.run_recurring` from a shell when testing

Also expose `POST /api/recurring/:id/run-now` (already in `PHASE_2.md`) so you can test without waiting for cron.

---

## Review router

### When the pipeline returns a draft, decide:

```python
class ReviewRouter:
    def route(self, session, pipeline_result: PipelineResult) -> RouteDecision:
        """Returns either a preview (high confidence) or a review-queue write."""
        if pipeline_result.overall_confidence >= THRESHOLD:
            return RouteDecision.preview(pipeline_result)
        else:
            review_item = self._write_review_queue(session, pipeline_result, reason=...)
            return RouteDecision.review(review_item)
```

### Reasons:

- `low_ocr` — `ocr_confidence < 0.5` or missing amount/currency.
- `ambiguous_category` — classifier returned ≥2 categories within 0.15 of each other.
- `duplicate_suspect` — emitted by `ApplyTransactionService.create` when duplicate-check fires.

### Threshold

`PHASE_2.md` specifies default 0.7 and says "tune for weeks". Expose as `REVIEW_CONFIDENCE_THRESHOLD` env var. Log the confidence of every import for the first few weeks; build a histogram; adjust.

### Response shape

`POST /api/import/photo` changes its response from Phase 1:

```json
{
  "data": {
    "kind": "preview",
    "previewTransaction": { ... },
    "confidence": 0.82,
    "ocrText": "...",
    "ocrEngine": "gpt-4o-mini",
    "llmModel": "gpt-4o-mini"
  }
}
```

or

```json
{
  "data": {
    "kind": "review",
    "reviewItemId": "rvw_abc123",
    "confidence": 0.45,
    "reason": "low_ocr"
  }
}
```

Frontend dispatches on `data.kind`. `PHASE_2.md` §"Updated Phase 1 endpoint" has the same shape in TS.

---

## API additions

All defined in `PHASE_2.md` §"API additions". Implementation notes only:

### Transactions — extended filters

```
GET /api/transactions
  ?account=acc_boa,acc_cash
  ?type=normal,transfer_out,transfer_in,recurring
  (plus Phase 1 filters)
```

Default for dashboard sums: `type=normal` (exclude transfers and recurring? see note below). Default for `/records`: all types.

**Open question on recurring:** should recurring transactions count toward month-flow on the dashboard? `PHASE_2.md` says yes (they're real money leaving your account). The frontend dashboard passes `type=normal,recurring` for monthly totals, and filters transfers out entirely.

### Transfers

`POST /api/transfers` is the only create path. Do not accept `type='transfer_*'` in `POST /api/transactions`; return 400 with `code: "use_transfers_endpoint"`.

### Budgets

`GET /api/budgets` response includes computed `spent_cents` and `effective_limit_cents` (if rollover) per row. Compute at query time; don't store.

### Review queue

`POST /api/review/:id/approve` accepts an optional body of `Partial<TransactionInput>` — the user-edited draft. Merge with stored draft, validate, call `apply.create(..., skip_duplicate_check=True)` (the review queue already decided this was real), delete the review row.

### Normalize preview

`POST /api/normalize` is stateless. Takes `{ raw: string }`, returns what the engine would decide. Used by the import UI to preview normalization before the user commits. Don't write anything to the DB.

---

## Testing additions

### `tests/services/ledger/test_apply.py`

The most important test file in Phase 2. Cover:

- Create a transaction → account balance increases.
- Update amount → balance reflects delta.
- Update account_id → old balance decreases, new balance increases, both atomic.
- Delete → balance reverses.
- Delete during an error mid-cascade → transaction rolls back, no partial state (test this with a mock that raises).

### `tests/services/ledger/test_transfers.py`

- Create transfer → two rows, shared group_id, linked by `transfer_group_id`, excluded from spend totals.
- Delete one leg via group → both gone.
- Edit one leg via generic PATCH → 400.

### `tests/services/normalization/test_engine.py`

Parameterize with 20+ cases covering:

- Alias hit.
- Each stripper rule (JP 店 suffix, CN 店 suffix, store number, parenthetical location, branch tag).
- Brand table hit.
- Fallback + title-casing.
- Short-name guard (parens-only stripping shouldn't leave empty).

### `tests/services/recurring/test_worker.py`

- Rule due today + not paused → fires, creates transaction, advances next_run.
- Rule due today + paused → no-op.
- Rule due 2 months ago → fires once, advances once, doesn't backfill.
- Day-of-month 31 on February → clamps to month-end (28/29).

### `tests/api/test_review.py`

- Low-confidence import → 200, `kind: "review"`, `reviewItemId` present, no `transactions` row.
- Approve → `transactions` row created, review row deleted.
- Reject → review row deleted, no `transactions` row.

### `tests/integration/test_cascade_reconcile.py`

The smoke test from earlier:

- Create 20 transactions (mix of normal, transfer, recurring).
- Assert each account's `balance_cents` matches `opening_balance_cents + SUM(...)` from scratch.
- Delete half; assert again.
- `POST /api/accounts/:id/recompute-balance` produces the same number.

---

## Migration order & data backfill

Seven new migrations, to run in order:

1. `0002_accounts.py` — create `accounts` table.
2. `0003_transactions_extend.py` — add new columns, backfill default Cash account, tighten NOT NULL on `account_id`.
3. `0004_merchants.py` — create `merchants` + `merchant_aliases`; seed from `merchants_seed.py`; backfill `merchant_normalized` by running `NormalizationEngine.normalize()` over every existing row.
4. `0005_budgets.py` — create `budgets` table. No data migration (empty on upgrade).
5. `0006_recurring.py` — create `recurring_rules` table.
6. `0007_review_queue.py` — create `review_queue` table.
7. `0008_seed_transfer_category.py` — add the system `transfer` category (undeletable, excluded from spend totals everywhere).

Run in sequence with `alembic upgrade head`. Step 3 is the slow one — if you have >10k transactions, write it as a chunked script instead of a single UPDATE.

---

## Checklist before calling Phase 2 done

- [ ] `alembic upgrade head` on a Phase 1 database produces a working Phase 2 database, with `balance_cents` correct on all accounts and `merchant_normalized` populated on all transactions.
- [ ] CRUD on accounts; net worth in the dashboard = SUM of balances across accounts.
- [ ] Creating / editing / deleting a transaction updates the account balance atomically (verified by recompute smoke test).
- [ ] Transfer endpoint creates two linked rows; both excluded from spend totals on `GET /api/transactions?type=normal`.
- [ ] At least one budget exists, and `GET /api/budgets` returns live `spent_cents` for the current period.
- [ ] Budget rollover works: create a budget in a prior period, leave it unspent, verify the next period's `effective_limit_cents` includes the carry.
- [ ] `POST /api/recurring/:id/run-now` fires a rule and creates a transaction linked back via `recurring_rule_id`.
- [ ] The scheduled worker (cron) actually runs in your deployment, and re-running it on the same day is a no-op.
- [ ] A low-confidence `POST /api/import/photo` returns `{kind: "review"}`, writes to `review_queue`, and doesn't touch `transactions`.
- [ ] Approving a review item via `POST /api/review/:id/approve` creates the transaction and removes the review row.
- [ ] Duplicate suspect: upload the same receipt twice within 48h — second upload routes to review with `reason="duplicate_suspect"`.
- [ ] Merchant normalization: `POST /api/normalize` with `{ raw: "Starbucks 徐家汇店" }` returns `{ normalized: "Starbucks", matchedBy: "strip" | "brand" }`.
- [ ] `pytest` passes, ≥60 tests across all layers.
- [ ] `PHASE_2.md` checklist's frontend-facing items all work end-to-end.

---

## Stack questions to answer before starting

1. **Cascade strategy** — service function (`ApplyTransactionService`, recommended) or DB triggers? Service is easier to debug in Python, triggers are marginally safer under concurrent writes (not a concern single-user).
2. **Recurring scheduler** — Fly.io cron, Railway Cron, Supabase pg_cron, GitHub Actions on a schedule, system cron on your server, APScheduler embedded in the FastAPI app? Embedded APScheduler is seductive but fragile — separate process is boringer and better.
3. **Review threshold** — default 0.7, expose via `REVIEW_CONFIDENCE_THRESHOLD` env var. Plan to tune.
4. **Normalization LLM fallback** — pure rules-based, or does the engine fall through to LLM when steps 1–3 miss? Rules-only is fine for Phase 2; add LLM fallback in Phase 3 if you see too many falsely-distinct merchants.
5. **Account archival behavior** — soft-delete (`archived=true`, hide from UI, forbid new transactions) or hard-delete with cascade? Soft is safer; `PHASE_2.md` says 409 on hard delete if transactions reference. Go soft.
6. **Transfer category color** — `transfer` gets a neutral color (grey recommended) so it visually doesn't look like spend. Consistent across light/dark themes.
