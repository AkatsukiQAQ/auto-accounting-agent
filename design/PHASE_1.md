# Phase 1 — "Capture tool with a nice face"

**Scope:** wire the existing OCR pipeline to a working frontend. Ship a deployable
personal tool you can actually use. **That's it.**

**Estimated effort:** 2–3 days.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md), [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md), and the `design-references/` folder (visual reference only — ignore screens not listed below).

---

## What you build in Phase 1

Exactly these screens from the prototype:

| Route | Prototype source | Notes |
|---|---|---|
| `/` | `dashboard-a.jsx` (`DashboardA`) | **Hide the "Accounts" strip.** Top row = month flow + savings index only. |
| `/records` | `screens.jsx` (`RecordsScreen`) | Full list, filter, search, edit row, delete row. |
| `/import` | `screens.jsx` (`ImportScreen`) | Upload → pipeline preview → manual edit → save. |
| `/categories` | `screens.jsx` (`CategoriesScreen`) | CRUD over the categories table. |
| `/settings` | `screens.jsx` (`SettingsScreen`) | **Only** Profile, Appearance (theme toggle only — no language), API keys, About sections. |

**Chrome:** `SideNav` + `TopBar` from `chrome.jsx`. Top bar only needs avatar menu + search stub. No language picker.

## What you explicitly do NOT build in Phase 1

| Do not build | Why |
|---|---|
| Accounts screen, multi-account balances | Phase 2 — requires `accounts` table and transfer logic. |
| Budget screen (V1 or V2), savings goals | Phase 2 — needs `budgets` table + cascade with transactions. |
| Recurring transactions | Phase 2. |
| Review queue | Phase 2. |
| Chatbot panel (`ChatPanel`) | Phase 3. |
| Dashboard variants B and C | Phase 3. Ship A only. |
| Dark mode | Phase 3. Leave the toggle UI but have it no-op (or remove). |
| i18n (Japanese / Chinese) | Phase 3. Ship English only. |
| Pipeline config, notifications, privacy sections in Settings | Phase 3. |
| ⌘K search command palette | Phase 3. Placeholder input is fine. |
| Learning / rules inference on user corrections | Phase 3. |

If the prototype shows it and it's not in the "What you build" table above, skip it.

---

## Data model — Phase 1

Only two tables. Everything else is deferred.

### `categories`

```sql
CREATE TABLE categories (
  id           TEXT PRIMARY KEY,           -- slug: 'food', 'transport', ...
  label        TEXT NOT NULL,              -- display name, user-editable
  color_bg     TEXT NOT NULL,              -- hex, e.g. '#FCE5CE'
  color_dot    TEXT NOT NULL,              -- hex
  keywords     TEXT NOT NULL DEFAULT '[]', -- JSON array of strings; used by regex classifier
  auto_assign  BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order   INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Seed with the nine categories already in the prototype (see `CAT_COLORS` in `primitives.jsx`): Food, Transport, Shopping, Bills, Entertain, Health, Income, Rent, Other.

### `transactions`

```sql
CREATE TABLE transactions (
  id             TEXT PRIMARY KEY,              -- uuid
  occurred_at    TIMESTAMPTZ NOT NULL,          -- when the purchase happened
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  merchant       TEXT NOT NULL,
  amount_cents   BIGINT NOT NULL,               -- store in minor units. Negative = expense, positive = income.
  currency       TEXT NOT NULL,                 -- ISO 4217: 'USD', 'JPY', 'CNY', ...
  category_id    TEXT NOT NULL REFERENCES categories(id),
  source         TEXT NOT NULL CHECK (source IN ('photo', 'manual')),
  confidence     REAL,                          -- 0..1, null for manual entries
  note           TEXT,
  raw_image_url  TEXT,                          -- only for source='photo'
  raw_ocr_text   TEXT,                          -- only for source='photo'
  raw_ocr_engine TEXT,                          -- 'tesseract', 'paddle', etc.
  raw_llm_model  TEXT                           -- 'gpt-4o', 'claude-sonnet-4', etc.
);

CREATE INDEX idx_transactions_occurred_at ON transactions (occurred_at DESC);
CREATE INDEX idx_transactions_category    ON transactions (category_id);
```

### Phase-1 design choices (important)

- **No `accounts` table yet.** Don't add an `account_id` column on `transactions`. When Phase 2 adds it, you'll backfill all existing rows to a single "Cash" account.
- **No `type` column (expense / income / transfer).** Sign of `amount_cents` carries that: negative = expense, positive = income. Transfers come in Phase 2 as a separate table.
- **Currency is per-row, not global.** The top bar has no currency switcher by design — the pipeline auto-detects from the receipt. User's "default currency" (in Settings → Profile) is only for manual entries.

---

## API contract — Phase 1

REST, JSON. All endpoints return `{ data: T }` on success, `{ error: { code, message } }` on failure.

### Transactions

```
GET    /api/transactions
       ?from=2026-01-01&to=2026-04-30
       &category=food,transport
       &q=starbucks
       &limit=50&cursor=<opaque>
       → { data: Transaction[], nextCursor: string | null }

GET    /api/transactions/:id     → { data: Transaction }
POST   /api/transactions         body: TransactionInput     → { data: Transaction }
PATCH  /api/transactions/:id     body: Partial<TransactionInput> → { data: Transaction }
DELETE /api/transactions/:id     → { data: { ok: true } }
```

### Categories

```
GET    /api/categories           → { data: Category[] }
POST   /api/categories           body: CategoryInput         → { data: Category }
PATCH  /api/categories/:id       body: Partial<CategoryInput> → { data: Category }
DELETE /api/categories/:id       → { data: { ok: true } }
         -- reject with 409 if any transactions still reference it; suggest reassigning to 'Other'
```

### Import pipeline

```
POST   /api/import/photo         multipart: image
       → {
           data: {
             previewTransaction: TransactionInput, -- pre-filled, not yet saved
             confidence: number,
             ocrText: string,
             ocrEngine: string,
             llmModel: string | null
           }
         }

POST   /api/transactions        -- user accepts / edits, then POSTs the normal create route
```

Keep the pipeline a **two-step flow**: `POST /api/import/photo` returns a draft; the user reviews/edits in the UI; then `POST /api/transactions` commits it. Do **not** auto-save on OCR success — the preview step is the whole point of the Import screen.

### Settings

```
GET    /api/settings             → { data: Settings }
PATCH  /api/settings             body: Partial<Settings>    → { data: Settings }
```

`Settings` shape for Phase 1:

```ts
type Settings = {
  profile: {
    fullName: string;
    preferredName: string;     // agent uses this in greetings; falls back to first word of fullName
    email: string;
    timezone: string;          // IANA, e.g. 'Asia/Tokyo'
    defaultCurrency: string;   // ISO 4217; used for manual entries only
  };
  appearance: {
    theme: 'light' | 'dark';   // leave in schema even though Phase 1 ships light-only
  };
  apiKeys: {
    openaiKey?: string;
    anthropicKey?: string;
    googleKey?: string;
    // ...whichever providers your pipeline supports. Store as-is; show/hide in UI.
  };
};
```

Store settings as a single-row `user_settings` table (or a JSON blob keyed by user). Phase 1 is single-user; skip auth entirely unless you already have it.

---

## TypeScript types

Put these in `src/lib/types.ts` on the frontend; mirror in backend.

```ts
export type Category = {
  id: string;
  label: string;
  colorBg: string;
  colorDot: string;
  keywords: string[];
  autoAssign: boolean;
  sortOrder: number;
};

export type Transaction = {
  id: string;
  occurredAt: string;          // ISO 8601
  createdAt: string;
  merchant: string;
  amountCents: number;         // negative = expense
  currency: string;
  categoryId: string;
  source: 'photo' | 'manual';
  confidence: number | null;
  note: string | null;
  raw: {
    imageUrl: string | null;
    ocrText: string | null;
    ocrEngine: string | null;
    llmModel: string | null;
  } | null;
};

export type TransactionInput = Omit<Transaction, 'id' | 'createdAt'>;
```

---

## Checklist before calling Phase 1 done

- [ ] All five routes render and are navigable from the sidebar.
- [ ] Can upload a receipt image, see the pipeline preview, edit, and save it as a transaction.
- [ ] Can manually create a transaction from Import screen's "Manual" tab.
- [ ] Can edit and delete transactions from Records.
- [ ] Can CRUD categories.
- [ ] Dashboard numbers (monthly flow, savings index placeholder, recent records) all read from the real DB, not sample data.
- [ ] Design tokens from `styles.css` live in Tailwind config (or ported verbatim). No hardcoded hex codes in components.
- [ ] Deployed somewhere you can actually hit from your phone.
- [ ] You've used it for at least a few real receipts and it didn't break.

---

## Stack questions to answer before starting

Pick one answer for each. Commit, then tell Claude Code.

1. **Framework** — Next.js App Router, or Vite + React Router, or Remix?
2. **Styling** — Tailwind (port tokens to config), or raw CSS variables (drop `styles.css` in)?
3. **Database** — Postgres (Supabase / Neon), SQLite (Turso / local file), or something else?
4. **Image storage** — S3 / R2 / Supabase Storage / local filesystem?
5. **Auth** — single-user with a hardcoded session, or real auth (Clerk / Supabase Auth / NextAuth)? *For Phase 1, single-user is fine and much faster.*

Claude Code will make something working regardless, but if you leave these open it'll make choices you'll want to change later.
