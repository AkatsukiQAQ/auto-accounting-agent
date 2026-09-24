# Phase 2 — "Actually a finance system"

**Scope:** extend Phase 1 into a real personal-finance system. Multi-account
ledger, per-category budgets, recurring bills, and a review queue that gates
low-confidence captures before they hit the ledger.

**Estimated effort:** ~1 week.

**Prerequisite:** Phase 1 is deployed, running, and you've used it for a few days.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md), [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md), `PHASE_1.md` (for the baseline schema this phase extends), and `design-references/`.

> **Start a fresh Claude Code session.** Don't continue the Phase 1 session — old
> context will drag in assumptions from the smaller schema and make cascade logic
> muddier. New session, give it `HANDOFF.md` + `DESIGN_SYSTEM.md` + `PHASE_1.md`
> (for schema reference) + this file + design references.

---

## What you build in Phase 2

### New screens (un-hide in sidebar)

| Route | Prototype source | Purpose |
|---|---|---|
| `/accounts` | `new-screens.jsx` (`AccountsScreen`) | Net worth · per-account balance cards · per-account transaction list · link new account. |
| `/budget` | `new-screens.jsx` (`BudgetScreenV2`) — replaces Phase 1's `BudgetScreen` | Per-category monthly caps · status pills (on track / warning / over) · savings goals. |
| `/recurring` | `new-screens.jsx` (`RecurringScreen`) | Subscription / bill list · next-run · pause / edit · auto-generate into ledger. |
| `/review` | `new-screens.jsx` (`ReviewQueueScreen`) | Low-confidence photo captures waiting for approval · approve / edit / reject. |

### Dashboard updates

- **Un-hide the Accounts strip** on `DashboardA`. Total = sum of account balances. Sparklines per account.
- Replace the Phase-1 "savings index placeholder" card with a real number derived from `budgets`.
- Recent records on the dashboard should show account name + category pill.

### Settings updates

- Un-hide "Notifications" section (budget-threshold alerts depend on this phase's data).
- Leave "Privacy" and "Pipeline config" for Phase 3.

---

## What you explicitly do NOT build in Phase 2

| Do not build | Why |
|---|---|
| Chatbot panel | Phase 3. |
| Dashboard variants B and C | Phase 3. |
| Dark mode wiring (beyond token definitions) | Phase 3. |
| i18n | Phase 3. |
| Learning from user corrections / auto-rules | Phase 3. |
| Annual Wrapped-style report | Phase 3. |
| Bank sync / Plaid integration | Out of scope entirely for now. Accounts are **manually created and updated** in Phase 2. |

---

## Data model additions

Keep Phase 1's `transactions` and `categories` tables. Add the following.

### `accounts`

```sql
CREATE TABLE accounts (
  id             TEXT PRIMARY KEY,                       -- slug or uuid
  name           TEXT NOT NULL,                           -- 'BoA Checking', 'Chase Sapphire', 'Cash'
  kind           TEXT NOT NULL CHECK (kind IN ('checking','savings','credit','cash','investment','other')),
  currency       TEXT NOT NULL,                           -- each account is single-currency
  balance_cents  BIGINT NOT NULL DEFAULT 0,               -- materialized; updated by cascade
  opening_balance_cents BIGINT NOT NULL DEFAULT 0,        -- source of truth for reconstruction
  institution    TEXT,
  color          TEXT,                                    -- optional hex, for the account card
  archived       BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order     INTEGER NOT NULL DEFAULT 0,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Extend `transactions`

```sql
ALTER TABLE transactions
  ADD COLUMN account_id TEXT REFERENCES accounts(id),
  ADD COLUMN type TEXT NOT NULL DEFAULT 'normal'
    CHECK (type IN ('normal','transfer_out','transfer_in','recurring')),
  ADD COLUMN transfer_group_id TEXT,                      -- links the two legs of a transfer
  ADD COLUMN recurring_rule_id TEXT,                      -- set when auto-generated from a rule
  ADD COLUMN merchant_raw TEXT,                           -- original OCR text, e.g. "Starbucks 徐家汇店"
  ADD COLUMN merchant_normalized TEXT;                    -- brand-level, e.g. "Starbucks" — what we display & match rules on
```

Rename the Phase 1 `merchant` column's semantics: from now on, `merchant` always holds the **normalized** brand name (what the UI shows, what rules match against). `merchant_raw` holds the full OCR'd string (what the receipt actually said — useful for audit and review). Both are displayed in the transaction detail view; list views show normalized only.

**Migration:** create a single `Cash` account and backfill `transactions.account_id` → `NOT NULL`. Also copy existing `merchant` values into `merchant_raw` (we have no normalization history for pre-P2 rows), and re-run normalization on all rows to populate `merchant_normalized` / overwrite `merchant`.

### Merchant normalization rules

The pipeline runs a **normalization step** after structuring, before classification. Goal: collapse `"Starbucks 徐家汇店"`, `"STARBUCKS #3341"`, `"星巴克 (南京西路店)"` all to `"Starbucks"` so the classifier and learned rules see one brand.

Strategy — apply in order, keep the first that matches:

1. **User-defined merchant aliases** — see `merchant_aliases` table below. Highest priority so the user can always override.
2. **Strip location / store suffixes** — regex removes common patterns:
   - Chinese store suffixes: `\s*[（(].*[店号铺馆厅)）]$`, `\s*\S+?店$`, `\s*\S+?分店$`
   - Store numbers: `\s*#?\d{2,}\s*$`, `\s*No\.?\s*\d+\s*$`
   - Branch indicators: `\s*[-–—]\s*.+?\s*(branch|store|outlet|location)$` (case-insensitive)
   - Parenthetical location: `\s*\(.+?\)\s*$` (last, because it's aggressive — skip if removing would leave <3 chars)
3. **Brand table lookup** — maintain a seeded `merchants` table of known brands with alias lists (see below). If the stripped name matches any alias, use the canonical brand name.
4. **Fall back** — use the stripped name as-is. Title-case it if it's all-caps.

Store both inputs and outputs: the user can always view `merchant_raw` and edit `merchant_normalized` by hand in the transaction detail view.

### `merchants` (brand table, seeded + grows from learning)

```sql
CREATE TABLE merchants (
  id                TEXT PRIMARY KEY,                    -- slug: 'starbucks', 'uber', 'meituan'
  canonical_name    TEXT NOT NULL,                        -- 'Starbucks', 'Uber', '美团'
  aliases           JSONB NOT NULL DEFAULT '[]',          -- ["STARBUCKS", "星巴克", "Starbucks Coffee"]
  default_category_id TEXT REFERENCES categories(id),    -- auto-suggest when this merchant appears
  logo_url          TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  source            TEXT NOT NULL CHECK (source IN ('seed','user','learned'))
);
```

Seed with the ~50 most common merchants for your target geography (Starbucks, Uber, Didi, Meituan, Amazon, 7-Eleven, etc.). New brands get inserted with `source='learned'` when the normalization falls through to step 4 **and** the same stripped name appears in ≥3 transactions — at that point, promote it to a `merchants` row so future corrections aggregate.

### `merchant_aliases` (user overrides)

```sql
CREATE TABLE merchant_aliases (
  id             TEXT PRIMARY KEY,
  raw_pattern    TEXT NOT NULL,                           -- substring or regex user wants matched
  match_type     TEXT NOT NULL CHECK (match_type IN ('contains','exact','regex')),
  merchant_id    TEXT NOT NULL REFERENCES merchants(id),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  applied_count  INTEGER NOT NULL DEFAULT 0
);
```

When the user edits `merchant_normalized` on an existing transaction, offer: *"Always normalize `Starbucks 徐家汇店` to `Starbucks`?"* On yes, write a `merchant_aliases` row. Same interaction pattern as the classification-rule learning in Phase 3.

### Transfers

A transfer is **two rows** in `transactions` sharing a `transfer_group_id`:
- `type='transfer_out'`, `account_id=A`, negative `amount_cents`
- `type='transfer_in'`,  `account_id=B`, positive `amount_cents`

Both rows share the same `merchant` ("Transfer to B" / "Transfer from A"), `occurred_at`, and a synthetic "Transfer" category. Transfers are **excluded from income/expense totals** everywhere (dashboard sums, budgets, monthly flow). Filter with `WHERE type = 'normal'` for anything spend-related.

### `budgets`

```sql
CREATE TABLE budgets (
  id             TEXT PRIMARY KEY,
  category_id    TEXT NOT NULL REFERENCES categories(id),
  period         TEXT NOT NULL CHECK (period IN ('month','week')),
  limit_cents    BIGINT NOT NULL,
  currency       TEXT NOT NULL,
  rollover       BOOLEAN NOT NULL DEFAULT FALSE,          -- unused budget carries to next period
  starts_on      DATE NOT NULL,                           -- first period start
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (category_id, period)                            -- one budget per category per period
);
```

### `recurring_rules`

```sql
CREATE TABLE recurring_rules (
  id            TEXT PRIMARY KEY,
  merchant      TEXT NOT NULL,
  amount_cents  BIGINT NOT NULL,                          -- negative = expense
  currency      TEXT NOT NULL,
  category_id   TEXT NOT NULL REFERENCES categories(id),
  account_id    TEXT NOT NULL REFERENCES accounts(id),
  cadence       TEXT NOT NULL CHECK (cadence IN ('monthly','weekly','yearly','custom')),
  day_of_month  INTEGER,                                  -- for monthly; 1..31 (clamp to month end)
  day_of_week   INTEGER,                                  -- for weekly; 0..6
  next_run_on   DATE NOT NULL,
  last_run_on   DATE,
  paused        BOOLEAN NOT NULL DEFAULT FALSE,
  note          TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

A cron/worker runs daily: for each rule where `paused=false AND next_run_on <= today`, insert a `transactions` row with `type='recurring'` and `recurring_rule_id=rule.id`, then bump `next_run_on` forward one cadence step. The generated transaction counts in budgets and balances like any normal one.

### `review_queue`

```sql
CREATE TABLE review_queue (
  id             TEXT PRIMARY KEY,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  draft          JSONB NOT NULL,                          -- pre-filled TransactionInput
  confidence     REAL NOT NULL,
  reason         TEXT NOT NULL,                           -- 'low_ocr', 'ambiguous_category', 'duplicate_suspect'
  image_url      TEXT,
  ocr_text       TEXT,
  suggested_category_id TEXT REFERENCES categories(id),
  alternate_categories  JSONB                             -- [{categoryId, score}, ...]
);
```

**Phase 1 behavior change:** `POST /api/import/photo` no longer returns a direct preview. If confidence is below a threshold (default 0.7), the item goes into `review_queue` and the response tells the UI to navigate to `/review`. Above threshold, it still returns the preview as in Phase 1 — nothing changes for high-confidence captures.

---

## Cascade rules — READ THIS BEFORE WRITING ANY MUTATION ENDPOINT

Getting these wrong is the #1 source of bugs in finance apps. Implement them as **database triggers** or as a single `applyTransaction()` service function that all mutation routes call — never scattered across handlers.

### When a `transactions` row is **inserted**:
1. `accounts.balance_cents += row.amount_cents` for `row.account_id`.
2. If `row.type = 'normal'` and a `budgets` row exists for `(row.category_id, current period)`, the budget's "spent" is recomputed (don't materialize; compute on read).
3. If any existing transaction in the last 48h has the same `merchant_normalized` (NOT `merchant_raw`), `amount_cents`, and `account_id`, flag as a potential duplicate (create a `review_queue` entry with `reason='duplicate_suspect'` and DO NOT insert the row yet — return the suspected duplicate to the client).
4. Normalization runs during the import pipeline, not in a trigger — by the time an insert reaches the DB, `merchant_raw` and `merchant_normalized` should both be populated. For manual entries with no raw value, store `merchant_raw = merchant_normalized`.

### When a `transactions` row is **updated**:
1. If `amount_cents` or `account_id` changed, reverse the old effect on the old account, then apply the new effect on the new account. Atomic, single transaction.
2. If `category_id` changed, the budget display updates next read — no stored value to mutate.
3. Transfers: if you edit one leg of a transfer, the other leg must be kept in sync (same `occurred_at`, opposite `amount_cents`). Easiest: make the transfer editor edit both rows together.

### When a `transactions` row is **deleted**:
1. Reverse `amount_cents` on `accounts.balance_cents`.
2. For transfers, delete **both** rows in the `transfer_group_id`.

### When an `accounts.opening_balance_cents` is edited:
- `balance_cents = opening_balance_cents + SUM(transactions.amount_cents WHERE account_id = this)`. Recompute fully — don't diff.

### When a `recurring_rules` row fires:
- Insert the transaction (which triggers the rules above), then update `last_run_on` and advance `next_run_on`.

---

## API additions

### Merchants & aliases

```
GET    /api/merchants                       ?q=star → { data: Merchant[] }   -- for autocomplete
POST   /api/merchants                       body: MerchantInput
PATCH  /api/merchants/:id                   body: Partial<MerchantInput>

GET    /api/merchant-aliases                → { data: MerchantAlias[] }
POST   /api/merchant-aliases                body: { rawPattern, matchType, merchantId }
DELETE /api/merchant-aliases/:id

POST   /api/normalize                       body: { raw: string } → { data: { normalized: string, merchantId: string | null, matchedBy: 'alias'|'strip'|'brand'|'fallback' } }
     -- exposed so the import UI can preview normalization before the user saves
```

### Accounts

```
GET    /api/accounts                 → { data: Account[] }
POST   /api/accounts                 body: AccountInput     → { data: Account }
PATCH  /api/accounts/:id             body: Partial<AccountInput>
DELETE /api/accounts/:id             → 409 if transactions reference it; must reassign first
POST   /api/accounts/:id/reconcile   body: { actualBalanceCents } → creates an adjustment transaction
```

### Transfers

```
POST   /api/transfers
       body: { fromAccountId, toAccountId, amountCents, occurredAt, note }
       → { data: { outTransaction, inTransaction, transferGroupId } }

DELETE /api/transfers/:transferGroupId → deletes both legs
```

### Budgets

```
GET    /api/budgets                  → { data: Budget[] }   -- includes computed spent_cents for current period
POST   /api/budgets                  body: BudgetInput
PATCH  /api/budgets/:id              body: Partial<BudgetInput>
DELETE /api/budgets/:id
```

### Recurring

```
GET    /api/recurring                → { data: RecurringRule[] }
POST   /api/recurring                body: RecurringRuleInput
PATCH  /api/recurring/:id            body: Partial<RecurringRuleInput>
DELETE /api/recurring/:id
POST   /api/recurring/:id/run-now    -- manually fire, useful for testing
```

### Review queue

```
GET    /api/review                   → { data: ReviewItem[] }
POST   /api/review/:id/approve       body: Partial<TransactionInput>  -- user-edited draft, commits to transactions
POST   /api/review/:id/reject        -- discards the item
```

### Updated Phase 1 endpoint

```
POST   /api/import/photo             -- changed behavior
       → {
           data:
             | { kind: 'preview', previewTransaction, confidence, ... }       -- high confidence, same as P1
             | { kind: 'review',  reviewItemId, confidence, reason }          -- queued, UI should go to /review
         }
```

### Updated `GET /api/transactions`

Add filters:
- `?account=acc_boa,acc_cash`
- `?type=normal,transfer_out,transfer_in,recurring` (default: all; dashboard passes `type=normal` for sums)

---

## TypeScript additions

```ts
export type Account = {
  id: string;
  name: string;
  kind: 'checking' | 'savings' | 'credit' | 'cash' | 'investment' | 'other';
  currency: string;
  balanceCents: number;
  openingBalanceCents: number;
  institution: string | null;
  color: string | null;
  archived: boolean;
  sortOrder: number;
};

export type Merchant = {
  id: string;
  canonicalName: string;
  aliases: string[];
  defaultCategoryId: string | null;
  logoUrl: string | null;
  source: 'seed' | 'user' | 'learned';
};

export type MerchantAlias = {
  id: string;
  rawPattern: string;
  matchType: 'contains' | 'exact' | 'regex';
  merchantId: string;
  appliedCount: number;
};

export type Budget = {
  id: string;
  categoryId: string;
  period: 'month' | 'week';
  limitCents: number;
  currency: string;
  rollover: boolean;
  startsOn: string;
  spentCents: number;         // computed server-side for current period
};

export type RecurringRule = {
  id: string;
  merchant: string;
  amountCents: number;
  currency: string;
  categoryId: string;
  accountId: string;
  cadence: 'monthly' | 'weekly' | 'yearly' | 'custom';
  dayOfMonth: number | null;
  dayOfWeek: number | null;
  nextRunOn: string;
  lastRunOn: string | null;
  paused: boolean;
  note: string | null;
};

export type ReviewItem = {
  id: string;
  createdAt: string;
  draft: Omit<Transaction, 'id' | 'createdAt'>;
  confidence: number;
  reason: 'low_ocr' | 'ambiguous_category' | 'duplicate_suspect';
  imageUrl: string | null;
  ocrText: string | null;
  suggestedCategoryId: string | null;
  alternateCategories: { categoryId: string; score: number }[] | null;
};
```

---

## Checklist before calling Phase 2 done

- [ ] Accounts CRUD works; net worth on dashboard = sum of balances.
- [ ] Creating / editing / deleting a transaction correctly updates its account balance.
- [ ] Transfers create two linked rows, both editable as a pair, both excluded from spend totals.
- [ ] At least one budget exists and the budget screen shows live spent vs limit for the current month.
- [ ] Budget status pill colors match the thresholds in the prototype.
- [ ] A recurring rule can be created; running it (manually via `run-now`) inserts a transaction that hits the right account and budget.
- [ ] The daily cron/worker actually runs in your deployment (not just locally).
- [ ] Low-confidence photo imports land in `/review` instead of the ledger.
- [ ] Approving a review item writes a real transaction and removes it from the queue.
- [ ] Duplicate detection catches an obvious same-amount-same-merchant import within 48h.

---

## Stack questions to answer before starting

1. **Cascade implementation** — DB triggers, or a single `applyTransaction()` service function everything routes through? (Service function is usually better for a 1-person project — easier to debug.)
2. **Recurring cron** — Vercel Cron / GitHub Actions / system cron / Supabase pg_cron / in-app worker?
3. **Review-queue confidence threshold** — default 0.7, but set it as a configurable env var. You'll tune this for weeks.
