# Phase 3 — Agent intelligence & polish

**Scope:** everything that makes MITA feel like an actual agent instead of a
tracker. Learning rules, insights, chatbot, dark mode, i18n, alternate
dashboards. Ship these **one at a time** when you've used Phase 2 enough to
know what you actually want.

**Prerequisite:** Phase 2 is deployed and you've lived with it for a couple of weeks.

**Read alongside:** [`HANDOFF.md`](./HANDOFF.md), [`DESIGN_SYSTEM.md`](./DESIGN_SYSTEM.md), `PHASE_1.md` and `PHASE_2.md` for the cumulative frontend scope, and `BACKEND_PHASE_1.md` + `BACKEND_PHASE_2.md` for the cumulative backend scope.

> **Phase 3 backend work is inlined here, not split into a `BACKEND_PHASE_3.md`.** Each feature below is small enough that its backend + frontend pieces fit in the same spec. Pick a feature, ship both sides in one Claude Code session (or two, if splitting front / back helps focus).

> **Start a fresh Claude Code session per feature.** Phase 3 is not one sprint —
> it's a rolling backlog. Each feature below is independent; scope one per session.

---

## Phase 3 is a menu, not a sprint

Pick items off this list based on what's actually annoying you about the Phase 2
product. Don't commit to building the whole list up front.

### Tier A — highest leverage (do these first)

#### A1. Classification rules + learning
When the user changes a transaction's category, offer: *"Always classify **Starbucks** as **Coffee**?"* On yes, write a row to `classification_rules`, and apply it on future OCR captures before the LLM classifier runs.

- New table: `classification_rules { id, pattern (TEXT), match_type ('exact'|'contains'|'regex'), category_id, created_at, applied_count, enabled }`.
- Settings → Pipeline section lists rules; user can edit / delete / disable.
- UI surface: a `CategoryLearnedToast` that pops when the rule triggers on a new capture.

**Backend work for A1:**
- Migration `0009_classification_rules.py` — table DDL.
- New service `services/classification/rules.py` — `apply_rules(merchant_normalized) -> Optional[category_id]`. Called from `ClassifyStage.run` **before** the regex-from-categories step. If a rule matches, short-circuit the LLM call and return `matched=True, keyword=rule.pattern, matched_by="rule"`.
- New endpoint group `/api/classification-rules` — GET / POST / PATCH / DELETE. Validate `pattern` compiles (for `match_type='regex'`).
- Extend `PATCH /api/transactions/:id` to return an optional `learningSuggestion` field in the response when `category_id` changes: `{ suggestion: { merchantNormalized: "Starbucks", newCategoryId: "coffee", existingRuleId: null } }`. Frontend shows the "Always classify…" toast; on accept, POSTs to `/api/classification-rules`.
- Track `applied_count` by incrementing in `ClassifyStage` on every hit. Sort rules by `applied_count DESC` in the Settings list so the user sees which ones matter.

#### A2. Pipeline visualization in Import
Expose the actual OCR / structuring / classification steps with intermediate outputs the user can see and correct:
- "OCR said: *`$7.25 Blue Bottle Coffee Apr 21`*" — click to edit
- "Structuring extracted: merchant=`Blue Bottle`, amount=`7.25`, date=`Apr 21 2026`"
- "Classifier chose: **Food** (confidence 0.82). Alternatives: Coffee 0.71, Shopping 0.12."

Backend: make the pipeline return all intermediate stages, not just the final draft. Log each stage's output to the `transactions.raw_*` columns for audit.

**Backend work for A2:**
- The `PipelineResult` dataclass from `BACKEND_PHASE_1.md` already holds every stage's output. Most of the work is exposing it.
- Change `POST /api/import/photo` response to include a `stages` array:
  ```ts
  stages: [
    { name: 'ocr',       output: { rawText, durationMs } },
    { name: 'parse',     output: { merchant, amount, currency, date } },
    { name: 'normalize', output: { merchantRaw, merchantNormalized, matchedBy } },  // from BACKEND_PHASE_2
    { name: 'classify',  output: { categoryId, alternates: [{categoryId, score}, ...], matchedBy } },
  ]
  ```
- Add `POST /api/import/rerun-stage` — given a review/preview id and a stage name + patched input, re-run downstream stages only. Lets the user correct an OCR error and see the new classification without re-uploading.
- Persist the full stages JSON to a new `transactions.pipeline_trace JSONB` column (migration `0010_pipeline_trace.py`) on successful commit — useful for auditing and for A1 rule suggestions ("this was classified by rule X").

#### A3. Dark mode
The tokens already exist. Wire the theme toggle in Settings → Appearance to flip `<body data-theme="dark">`. Persist to `settings.appearance.theme`. Test every screen; pay attention to chart stroke colors and category pills.

**Backend work for A3:** none. `settings.appearance.theme` is already in the Phase 1 settings schema.

### Tier B — meaningful polish

#### B1. Chatbot (`ChatPanel`)
Right-docked overlay, 420px wide. Triggered by the orange FAB in the bottom-right of every screen, or ⌘K. Backed by your `claude.complete()`-style endpoint.

- Agent has tool access to read `transactions`, `accounts`, `budgets`.
- Greeting interpolates `settings.profile.preferredName` (falls back to first word of `fullName`).
- Suggestion chips above the input: "How much did I spend on food this month?" / "Am I on track with my rent budget?" / "What recurs next week?"

**Backend architecture for B1 — orchestrator pattern:**

This is the **first and only place LangGraph comes back**. The chatbot is legitimately agentic (multi-step reasoning, tool routing, conversation state); Phase 1-2 pipeline stages are not, and intentionally stayed off LangGraph. Keep that separation: don't let chatbot dependencies bleed into `services/pipeline/`.

Structure:

```
ChatOrchestrator (LangGraph StateGraph)
    │
    ├─ route_intent(message) ─────→ decides which subsystem to invoke
    │
    ├─ Simple-query tools (direct DB read, one-shot):
    │   ├─ get_transactions(from, to, category, account, type, limit)
    │   ├─ get_account_balances()
    │   ├─ get_budget_status(period)
    │   ├─ get_recurring_next_week()
    │   └─ get_top_merchants(from, to, limit)
    │
    └─ Complex-analysis tool:
        └─ run_analysis_agent(question, context)
              │
              └─ Delegates to a separate AnalysisAgent subgraph
                 that handles multi-step reasoning:
                 "Compare my food spending H1 this year vs last year
                  and explain the biggest contributors."
```

Design rules:

- **Orchestrator does routing + synthesis only.** It does not do its own complex reasoning. If a question needs multi-step analysis, it hands off to a sub-agent.
- **Simple-query tools are pure DB reads.** They return structured data; the orchestrator turns that into natural language in the final synthesis step. They are not themselves LLM calls.
- **Sub-agents are new StateGraphs, not more tools on the orchestrator.** As new capabilities land (budget-planning agent in B4, anomaly-detection in C?, etc.), each gets its own subgraph under `services/agent/subagents/`. The orchestrator gets one new tool per sub-agent: `run_<x>_agent(...)`. This keeps the orchestrator's prompt small and its routing logic inspectable.
- **Streaming via SSE.** `POST /api/chat/message` streams tokens + tool-call visualizations ("Looking up your budgets…"). The frontend's `ChatPanel` already has tool-call affordances — hook them up to these events.

Implementation scaffolding:

```
services/agent/
├── orchestrator.py         # ChatOrchestrator — the StateGraph
├── tools/
│   ├── transactions.py     # get_transactions
│   ├── accounts.py         # get_account_balances
│   ├── budgets.py          # get_budget_status
│   ├── recurring.py        # get_recurring_next_week
│   └── merchants.py        # get_top_merchants
├── subagents/
│   └── analysis.py         # AnalysisAgent — multi-step reasoning subgraph
└── state.py                # ChatState TypedDict (messages, session_id, scratchpad)
```

Other backend work for B1:

- `POST /api/chat/message` — body `{ sessionId, message }`, returns `text/event-stream`.
- Store chat history in new `chat_sessions` + `chat_messages` tables. Migration `0011_chat.py`.
- System-message preamble includes current-month summary (totals, top 3 categories) so trivial "how am I doing" questions don't spend a tool call.
- Rate-limit per session (100 messages/day) to cap LLM costs.
- Re-add LangGraph to `pyproject.toml` **only now**: `langgraph`, `langchain-core`, `langchain-openai`. Do not reintroduce `langchain` (the meta-package) — you don't need chains/agents/tools from it.

#### B2. i18n (JA / ZH)
Port `i18n.jsx`'s dictionary to your stack's i18n library (next-intl / react-i18next). The prototype already has strings for all Phase 1 + Phase 2 screens in en / ja / zh. Currency formatting follows `Intl.NumberFormat(locale, { currency })` — no custom logic.

**Backend work for B2:**
- Add `settings.profile.locale` field (`"en" | "ja" | "zh"`, defaulting to browser's `Accept-Language`). Migration not needed — it's inside the JSON `user_settings.data`.
- LLM prompts in the pipeline take a `locale` argument. Category labels returned by the agent/chatbot are translated server-side for consistency.
- Error messages returned by the API get a `messageKey` field in addition to `message`, so the frontend can localize: `{ error: { code, messageKey: "errors.category_in_use", message: "Category in use" } }`.

#### B3. Insights
- **Category drill-down**: click a category on the dashboard → month view → list of transactions in that category, sortable.
- **Top merchants**: "This month you spent the most at *Uber*, *Blue Bottle*, *Amazon*."
- **Month-over-month compare**: a small delta on every dashboard number.

**Backend work for B3:**
- New endpoint `GET /api/insights/summary?from=&to=` — returns `{ totals: { incomeCents, expenseCents, netCents }, byCategory: [{ categoryId, spentCents, txnCount }], byMerchant: [{ merchantNormalized, spentCents, txnCount }], momDelta: { incomePct, expensePct } }`. Single endpoint powers all three insights; cache for 60s if needed.
- Category drill-down is just `GET /api/transactions?category=X&from=&to=` — already works in Phase 1.
- MoM delta: compute against the same-length window ending at `from - 1 day`. Edge case: first month of data → return `null` for delta fields.

### Tier C — nice-to-haves

#### C1. Annual Wrapped
Year-end page, Spotify-style. Total spent, biggest splurge, most-used category, month with highest savings rate. Honestly the most fun thing to build.

**Backend work for C1:** one endpoint, `GET /api/insights/wrapped?year=2026`. Aggregates the year. Heavy query; cache the result to a `wrapped_cache` row keyed by year — compute once in late December, serve from cache.

#### C2. Dashboard variants B (Journal) and C (Control room)
Alternate layouts with the same data. Let the user switch in Settings → Appearance.

**Backend work for C2:** none. Same data, different presentation. Add `settings.appearance.dashboardVariant: 'a' | 'b' | 'c'`.

#### C3. CSV / bank-statement import
Batch ingest historical data so the user isn't screenshotting their entire past. Map columns → `transactions` fields with a small column-picker UI.

**Backend work for C3:**
- `POST /api/import/csv` — multipart CSV file + column mapping JSON `{ occurredAt: 0, merchant: 1, amountCents: 2, currency: 3 }`.
- Parses, validates, inserts in a single DB transaction via `ApplyTransactionService.create` in a loop (with `skip_duplicate_check=False` — dedup is the whole point).
- Returns `{ imported: N, skipped: M, errors: [{ row, reason }] }`. Don't fail the whole import on one bad row.
- Run merchant normalization + classification on every row. Reuse the existing pipeline's `ParseStage` + `NormalizationStage` + `ClassifyStage`, just skipping `OCRStage`.

#### C4. Goals
Long-term savings goals beyond monthly budgets. "Save $5k by December." Progress ring widget on the dashboard.

**Backend work for C4:** new `goals` table `{ id, name, target_cents, currency, target_date, account_id (optional), created_at }`. Progress = current balance of linked account OR manual "current_cents" field. Migration `0012_goals.py`. Standard CRUD endpoints.

#### C5. Export / backup
JSON export of the full DB, encrypted backup to S3/R2. Settings → Data & Privacy.

**Backend work for C5:** `GET /api/export/all` — streams a JSON with every table as an array. `POST /api/backup/trigger` — async job, uploads to configured S3 bucket with client-side encryption (user provides passphrase in Settings; derive a key via Argon2).

#### C6. Data & privacy controls
On-device processing toggle (run OCR locally if the user's machine can), telemetry opt-in, "delete everything" button.

**Backend work for C6:**
- `DELETE /api/account/purge` — wipes all user data. Require a confirmation token from a preceding `POST /api/account/purge/request` (sends token via email or displays inline for single-user).
- `settings.privacy.localProcessing: boolean` — when true, `POST /api/import/photo` routes OCR to a local model (e.g. Tesseract via `pytesseract`) before LLM structuring. Tradeoff: lower OCR quality, no data egress.
- `settings.privacy.telemetry: boolean` — gate all analytics events behind this flag.

---

## Order of operations I'd actually follow

1. **A1 (Rules & learning)** first. It's the single biggest quality-of-life jump — every category correction starts teaching the system.
2. **A2 (Pipeline visualization)** next. Once rules exist, the user needs to see *why* a capture was classified a certain way to write good rules.
3. **A3 (Dark mode)** — tokens already work, an afternoon's work, instant visible payoff.
4. **B1 (Chatbot)** — after rules + pipeline are mature, the agent has something interesting to talk about. A chatbot with no tool calls isn't worth building.
5. Everything else based on actual pain points.

Don't build B2 (i18n) unless you actually have non-English users. Don't build C2 (extra dashboards) unless A is bored of Variant A. Don't build C3 (CSV import) unless you need it for your own historical data.

---

## Checklist per feature

Each Tier-A / Tier-B feature is its own mini-phase. For each one:

- [ ] Pick it off this list.
- [ ] Start a fresh Claude Code session.
- [ ] Give it: `HANDOFF.md`, `DESIGN_SYSTEM.md`, `PHASE_3.md` (tell it which section to build), relevant design-reference files.
- [ ] Ship it, deploy it, use it for a few days.
- [ ] Pick the next feature.

Phase 3 doesn't have an "end". That's the point.
