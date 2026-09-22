# MITA Finance V2 — Budget-First Personal Finance Agent Redesign

> This document is the implementation brief / coding-agent prompt for the next major iteration of `AkatsukiQAQ/auto-accounting-agent`.
>
> The goal is **not** to build a more complicated accounting app. The goal is to pivot the existing Phase-1 product into a **budget-first personal finance operating system with an agentic control surface**.

---

## 0. Context

The existing repository already has a solid Phase-1 foundation:

- FastAPI backend
- SQLAlchemy + Alembic + SQLite
- React 19 + TypeScript + Vite + Tailwind
- Transaction/category/settings CRUD
- Receipt screenshot import pipeline
- Deterministic OCR → parse → classify pipeline
- Existing backend test suite
- A coherent warm-paper MITA Finance design system
- Dashboard / Records / Import / Categories / Settings screens

Do **not** throw these away.

The product direction has changed:

### Old product center

> “Automatically turn receipts/payment screenshots into detailed accounting records.”

### New product center

> “Help me control my spending against a realistic weekly/monthly plan, understand where my money is going, and let an AI agent help me change the plan.”

The user does **not** primarily care about keeping a perfect merchant-by-merchant ledger.

Individual transactions are useful supporting evidence, but the main product questions are:

1. How much did I plan to spend?
2. How much have I actually spent?
3. Which categories are at risk?
4. How much can I still safely spend?
5. Am I likely to stay within my monthly income?
6. What should I change next week / next month?
7. Can I ask the assistant to make those changes for me?

This should drive every product and architecture decision below.

---

# 1. Repository strategy

## Do NOT start a new repository

Continue from the current repository so we keep:

- Git history
- working Phase-1 pipeline
- tests
- frontend primitives
- current visual language
- API conventions
- transaction/category code that is still useful

Create a feature branch such as:

```bash
git checkout -b v2/budget-agent
```

Before implementation, preserve the old product plan:

```text
design/archive/v1/
  HANDOFF.md
  PHASE_2.md
  PHASE_3.md
  BACKEND_PHASE_2.md
```

Do not delete useful historical docs; archive them.

Then create the new V2 docs:

```text
design/V2_PRODUCT.md
design/V2_PHASE_1_BUDGET_CORE.md
design/V2_PHASE_2_AGENT.md
```

This file can become `design/V2_PRODUCT.md`.

### Important

Do **not** implement the old Phase 2 before doing this redesign.

The old Phase 2/3 plan contains useful ideas, but its priorities are wrong for the new product. In particular:

- Accounts / net worth are no longer a Phase-2 priority.
- Recurring-bill automation is useful but not core.
- Review queue is useful but not core.
- Budgeting must move to the center of the dashboard.
- Chat/agent should move much earlier.
- The product should support low-detail / aggregate spending input, not force detailed bookkeeping.

---

# 2. Product principles

## Principle A — Budget is the primary object

The app should open with:

> “What did I plan, what have I spent, what remains?”

not:

> “Here are my recent transactions.”

Transactions remain accessible, but they are secondary.

---

## Principle B — Support imperfect tracking

The app must work even if the user does **not** record every coffee, train ride, or meal.

A spending record may be:

1. A detailed imported transaction
2. A quick manual expense
3. A coarse aggregate adjustment

Examples:

```text
Food ¥1,200
Transportation ¥5,000
I think I spent about ¥12,000 on eating out this week
Set this month's alcohol spending to ¥8,500
```

The system should be useful without merchant-level completeness.

---

## Principle C — The LLM never owns arithmetic

All sums, comparisons, remaining amounts, budget percentages, period boundaries, and projections must be computed by deterministic Python/SQL services.

The LLM receives structured results and reasons over them.

Never ask the model to infer totals from raw transaction lists if a deterministic aggregation tool can compute them.

---

## Principle D — Chat is a control surface

Chat should not be a decorative chatbot.

It must be able to:

- inspect the user's budget state
- inspect spending summaries
- compare periods
- explain overspending
- propose next-week / next-month targets
- create or update budgets after confirmation
- add quick spending entries
- correct category totals
- trigger deterministic commands

If Chat cannot modify the system, it is not the main agent feature.

---

## Principle E — Writes are explicit and auditable

Read tools may execute automatically.

Meaningful write actions should be previewed before execution unless the user used an explicit deterministic slash command.

Example:

```text
User:
"Next week I want to be stricter on eating out."

Agent:
"Based on your last 4 weeks, I suggest reducing Dining from ¥18,000 to ¥12,000
for next week while leaving Groceries unchanged.

Apply this plan?"

[Apply] [Edit]
```

After Apply:

```text
✓ Dining budget for Sep 28–Oct 4 changed to ¥12,000
```

The action must be persisted in an audit log.

---

# 3. Design system — preserve it

The existing warm-paper MITA visual system is a keeper.

Continue using:

- cream paper surfaces
- ink typography
- Fraunces / handwritten accent typography
- PaperCard
- existing category pills
- subdued borders
- low visual noise
- no heavy shadows
- existing sidebar / top bar composition

Do **not** redesign the product into a generic SaaS dashboard.

The app should still immediately look like the current MITA Finance.

However, the information hierarchy of the Dashboard should change substantially.

---

# 4. New information architecture

Recommended primary navigation:

```text
Dashboard
Plan
Records
Import
Categories
Settings
```

Later:

```text
Dashboard
Plan
Records
Import
Insights
Settings
```

Chat is global and does not need its own route.

## De-prioritize for now

Do not make these first-class V2 navigation items yet:

- Accounts
- Net worth
- Recurring
- Review queue
- Savings-goal manager

They can return after the budget/agent loop is working.

---

# 5. Core domain model

The current `transactions` and `categories` tables should remain.

Add a budget layer above them.

## 5.1 `budget_plans`

A plan represents one concrete period.

```sql
CREATE TABLE budget_plans (
  id                    TEXT PRIMARY KEY,
  period_type           TEXT NOT NULL
    CHECK (period_type IN ('week', 'month')),

  starts_on             DATE NOT NULL,
  ends_on               DATE NOT NULL,
  currency              TEXT NOT NULL,

  planned_income_cents  BIGINT,
  savings_target_cents  BIGINT,

  status                TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('draft', 'active', 'closed')),

  note                  TEXT,
  created_by            TEXT NOT NULL DEFAULT 'user'
    CHECK (created_by IN ('user', 'agent', 'template')),

  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(period_type, starts_on, currency)
);
```

Examples:

```text
September 2026 monthly plan
Sep 28 – Oct 4 weekly plan
```

The app may have both an active monthly plan and an active weekly plan.

---

## 5.2 `budget_items`

Each plan contains category-level allocations.

```sql
CREATE TABLE budget_items (
  id                TEXT PRIMARY KEY,
  plan_id           TEXT NOT NULL REFERENCES budget_plans(id) ON DELETE CASCADE,
  category_id       TEXT NOT NULL REFERENCES categories(id),

  limit_cents       BIGINT NOT NULL,
  warning_ratio     REAL NOT NULL DEFAULT 0.80,

  kind              TEXT NOT NULL DEFAULT 'flexible'
    CHECK (kind IN ('fixed', 'flexible', 'discretionary')),

  note              TEXT,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(plan_id, category_id)
);
```

`kind` is useful for reasoning:

- `fixed`: rent, phone, subscriptions
- `flexible`: groceries, transportation
- `discretionary`: dining out, alcohol, hobbies, shopping

Do not hard-code which category belongs to which kind; make it configurable.

---

## 5.3 Extend `transactions` for low-friction input

Transactions are now evidence for spending, not necessarily detailed accounting records.

Add:

```sql
ALTER TABLE transactions ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';
ALTER TABLE transactions ADD COLUMN granularity TEXT NOT NULL DEFAULT 'transaction';
ALTER TABLE transactions ADD COLUMN note TEXT;
```

Recommended enums:

```text
source:
  manual
  slash
  agent
  receipt
  screenshot
  csv
  adjustment

granularity:
  transaction
  quick
  aggregate_adjustment
```

If the current schema requires a merchant, make merchant optional in the V2 model,
or introduce a neutral description field and allow records such as:

```text
category: Dining
amount: -12000
merchant: null
granularity: aggregate_adjustment
note: "Approximate dining spend for this week"
```

Do not invent fake merchants such as `"Manual Entry"` just to satisfy the schema.

---

# 6. Spending semantics

This is important.

The system should support three user intents:

## A. Add an expense

```text
/spend 1200 food
```

Creates:

```text
amount = -1200
category = food
granularity = quick
source = slash
```

---

## B. Add an aggregate expense

```text
"I spent about ¥12,000 eating out this week"
```

Creates one record:

```text
amount = -12000
category = dining
granularity = aggregate_adjustment
source = agent
```

This is deliberately allowed.

The app does not require 5 individual restaurant transactions.

---

## C. Set the category total

```text
"Set dining to ¥21,000 for this month."
```

Do **not** overwrite historical transactions.

Compute:

```text
current deterministic category spend = ¥17,500
desired total = ¥21,000
delta = ¥3,500
```

Create an adjustment record:

```text
amount = -3500
category = dining
granularity = aggregate_adjustment
source = adjustment
note = "Adjusted monthly total to ¥21,000"
```

This preserves an audit trail.

Later detailed imports can create reconciliation problems; do not attempt automatic
reconciliation in V2 Phase 1. Display aggregate adjustments clearly in Records so
the user can delete/reverse them if better data becomes available.

---

# 7. Budget computation service

Create a deterministic service such as:

```text
backend/services/budget/
  periods.py
  summary.py
  projections.py
  mutations.py
```

Important functions:

```python
get_active_plan(period_type, on_date)
get_plan_summary(plan_id)
get_item_status(plan_id, category_id)
get_period_spend(category_id, start, end, currency)
compare_periods(current_start, current_end, previous_start, previous_end)
project_period_end(plan_id, as_of)
set_category_spend_total(...)
clone_plan(source_plan_id, new_start, new_end)
```

Return structured values such as:

```json
{
  "planId": "...",
  "period": {
    "type": "month",
    "startsOn": "2026-09-01",
    "endsOn": "2026-09-30",
    "daysElapsed": 22,
    "daysRemaining": 8
  },
  "plannedIncomeCents": 30000000,
  "plannedSpendCents": 24000000,
  "actualSpendCents": 19100000,
  "remainingBudgetCents": 4900000,
  "projectedSpendCents": 26100000,
  "projectedSavingsCents": 3900000,
  "items": [
    {
      "categoryId": "dining",
      "limitCents": 4500000,
      "spentCents": 3900000,
      "remainingCents": 600000,
      "usedRatio": 0.867,
      "paceRatio": 1.18,
      "status": "warning"
    }
  ]
}
```

### Status logic

Implement deterministic status values:

```text
safe
watch
warning
over
```

Do not have the LLM decide these.

A simple first rule is enough:

- `over`: spent > limit
- `warning`: used ratio >= 0.8 and spending pace is above time pace
- `watch`: used ratio >= 0.6
- `safe`: otherwise

Keep thresholds configurable.

---

# 8. Dashboard V2

This is the biggest frontend change.

The Dashboard should answer:

> “Am I okay this week / this month?”

## 8.1 Hero area

Keep the current greeting style.

Add a prominent period switch:

```text
[ Week ] [ Month ]
```

and previous / next period controls.

---

## 8.2 Main KPI row

Replace transaction-centric KPIs with:

```text
Planned income
Spent
Remaining
Projected end-of-period
```

Optionally include:

```text
Savings target
Projected savings
```

Do not give “transaction count” equal visual weight.

---

## 8.3 Budget bucket section

This is the center of the page.

Each category card/row should show:

```text
Dining
¥39,000 / ¥45,000
████████████████░░ 87%
¥6,000 left
▲ ahead of pace
```

Support grouping by:

```text
Fixed
Flexible
Discretionary
```

Sort riskier items first by default.

---

## 8.4 “Safe to spend” indicator

Calculate a deterministic suggested remaining daily / weekly allowance:

```text
Remaining flexible budget / remaining days
```

Example:

```text
Safe flexible spend
¥4,800 / day
```

This should be a supporting indicator, not a moral judgment.

---

## 8.5 Agent insight card

Add one small card:

```text
MITA noticed

Dining is 18% ahead of your monthly pace.
If the current trend continues, you may exceed the plan by ~¥7,000.

[Ask MITA] [Adjust plan]
```

For Phase 1 this can be generated deterministically from the summary.

Do not require the agent backend yet.

---

## 8.6 Move recent records down

Recent transactions remain available but move below the budget state.

A transaction feed is no longer the dashboard's main content.

---

# 9. Plan screen

Create `/plan`.

This is where the user edits the active weekly/monthly plan.

Support:

- period selector
- planned income
- savings target
- category limits
- category kind
- total planned spending
- unallocated amount

Important invariant:

```text
planned income - planned spending = planned residual
```

Do not force residual to zero.

The user may intentionally leave a buffer.

Provide:

```text
Duplicate last week
Duplicate last month
Create blank plan
```

These should be deterministic actions.

---

# 10. Quick entry

Keep the existing Import flow.

Also create a much faster manual entry path.

Example compact UI:

```text
Amount      ¥ [      ]
Category    [ Dining ▾ ]
Date        [ Today ]
Note        [ optional ]

[ Add expense ]
```

Merchant is optional.

This should take only a few seconds.

---

# 11. Agent architecture — V2 Phase 2

Do not implement this until the deterministic budget core is working.

The chat system should use the same backend services as the normal UI.

The agent must never bypass service-layer validation.

Recommended structure:

```text
backend/services/agent/
  orchestrator.py
  state.py

  tools/
    budget_read.py
    spending_read.py
    transactions.py
    budget_write.py

  prompts/
    system.md
    budget_planner.md
```

For the first version, prefer a straightforward tool-calling loop over a complicated multi-agent graph.

LangGraph is optional.

Use it only if conversation state / multi-step orchestration actually becomes complex.

---

# 12. Agent tool contract

## Read tools

```text
get_current_plan(period_type)
get_plan_summary(plan_id)
get_spending_breakdown(from, to)
compare_spending(period_a, period_b)
get_category_history(category_id, periods=4)
get_recent_entries(category_id?, limit?)
```

## Write tools

```text
create_budget_plan(...)
set_budget_item_limit(plan_id, category_id, limit_cents)
set_planned_income(plan_id, amount_cents)
set_savings_target(plan_id, amount_cents)
add_quick_expense(...)
set_category_spend_total(...)
clone_budget_plan(...)
```

All tools return structured typed results.

---

# 13. Agent write policy

### Reads

Execute automatically.

### Explicit slash writes

May execute directly because the intent is unambiguous.

Example:

```text
/budget dining 12000 next-week
```

### Natural-language writes

Preview first.

Example:

```text
"I want to spend less next week."
```

The model may analyze and propose a plan, but must not silently write it.

Return a structured pending action:

```json
{
  "type": "budget_plan_patch",
  "summary": "Reduce Dining to ¥12,000 and Shopping to ¥5,000 next week",
  "operations": [...]
}
```

The frontend renders:

```text
[ Apply changes ] [ Edit ]
```

Only Apply calls the write endpoint.

---

# 14. Slash commands

Slash commands are deterministic UI shortcuts.

They should be parsed before the LLM.

Initial set:

```text
/spend <amount> <category>
/income <amount> [note]
/budget <category> <amount> [week|month|next-week|next-month]
/set-spent <category> <amount> [week|month]
/summary [week|month]
/plan next-week
/plan next-month
/undo
```

Examples:

```text
/spend 1800 dining
/budget dining 12000 next-week
/set-spent alcohol 8500 month
/summary month
```

`/plan next-week` may invoke the planning agent later.

For V2 Phase 1, it can simply clone the current week.

---

# 15. Chat UX

Reuse the existing visual direction for `ChatPanel`.

Recommended interaction:

```text
User: How am I doing this month?

MITA:
You've spent ¥191,000 of a ¥240,000 plan.

The main risk is Dining:
¥39,000 / ¥45,000 with 8 days remaining.

At your current pace, total spending is projected around ¥261,000.

[Make a recovery plan]
```

Clicking the suggestion can generate:

```text
Suggested remaining 8-day plan

Dining       ¥6,000 remaining
Shopping     ¥3,000 remaining
Entertainment ¥2,000 remaining

Expected month-end spend: ~¥239,000

[Apply] [Edit]
```

---

# 16. Agent audit log

Add:

```sql
CREATE TABLE agent_actions (
  id              TEXT PRIMARY KEY,
  session_id      TEXT,
  action_type     TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  status          TEXT NOT NULL
    CHECK (status IN ('proposed', 'confirmed', 'executed', 'cancelled', 'failed')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  executed_at     TIMESTAMPTZ
);
```

This is useful for:

- undo
- debugging
- trust
- inspecting incorrect agent behavior

Do not store hidden chain-of-thought.

Store only the user-visible/action-relevant structured proposal and result.

---

# 17. APIs for V2 Phase 1

Minimum API surface:

```text
GET    /api/budget-plans?periodType=&from=&to=
GET    /api/budget-plans/:id
POST   /api/budget-plans
PATCH  /api/budget-plans/:id
DELETE /api/budget-plans/:id

POST   /api/budget-plans/:id/clone

POST   /api/budget-plans/:id/items
PATCH  /api/budget-items/:id
DELETE /api/budget-items/:id

GET    /api/budget-plans/:id/summary
GET    /api/budget-summary/current?periodType=week|month

POST   /api/transactions/quick
POST   /api/budget-spend/set-total
```

Keep camelCase DTOs consistent with the existing API.

---

# 18. V2 Phase 1 — implementation scope

This is the **next implementation phase**.

Build only the budget core first.

## Backend

1. Add migrations for:
   - `budget_plans`
   - `budget_items`
   - transaction V2 metadata

2. Add budget domain/service layer.

3. Add deterministic aggregation and status computation.

4. Add period helpers for ISO-style weeks and calendar months.

5. Add quick expense endpoint.

6. Add “set category total” adjustment logic.

7. Add plan CRUD + clone.

8. Add tests for:
   - weekly boundaries
   - month boundaries
   - plan aggregation
   - adjustment delta
   - status calculation
   - projection
   - clone behavior
   - currency isolation

## Frontend

1. Redesign Dashboard around budget state.
2. Add Week / Month toggle.
3. Add category budget progress section.
4. Add `/plan`.
5. Add quick expense modal/form.
6. Keep Records and Import working.
7. Keep current visual tokens/components.
8. Move recent transactions below budget content.

---

# 19. Explicitly OUT OF SCOPE for V2 Phase 1

Do not build:

- chatbot backend
- LangGraph orchestration
- accounts / net worth
- bank sync
- recurring worker
- review queue
- notification system
- CSV import
- annual wrapped
- savings goals with separate accounts
- auto-generated AI recommendations
- multi-user authentication
- complicated forecasting ML

The Phase-1 goal is to make the deterministic product useful enough that the user can genuinely manage one week and one month with it.

---

# 20. V2 Phase 2 — agent scope

Only after V2 Phase 1 is dogfooded.

Build:

1. Global ChatPanel
2. chat sessions/messages
3. deterministic slash-command parser
4. read tools
5. budget write tools
6. pending-action confirmation UX
7. agent action log
8. streaming responses
9. next-week planning flow
10. compare / explain spending flow

A useful minimum demo:

```text
User:
"How am I doing this month?"

Agent:
reads current plan
reads summary
identifies risky categories
explains them

User:
"Help me set a stricter plan for next week."

Agent:
reads last 4 weekly summaries
proposes new limits
shows expected total
asks for confirmation

User:
Apply

Agent:
writes next week's plan

Dashboard updates immediately.
```

That is the core agentic loop.

---

# 21. Existing code to preserve

Do not casually rewrite these areas:

- existing import pipeline
- pipeline LLM abstraction
- category CRUD
- settings CRUD
- API error conventions
- frontend fetch wrapper
- TanStack Query pattern
- PaperCard / Button / Icon / CatPill primitives
- formatter utilities
- existing design tokens
- existing transaction CRUD unless schema changes require a focused migration

Use existing conventions before creating new ones.

---

# 22. Existing code/product concepts to de-emphasize

These can remain functional, but should not dominate V2:

- merchant normalization
- perfect receipt classification
- account balance / net worth architecture
- detailed recurring transaction automation
- review queues
- transaction count as a KPI
- merchant-centric insights

They are optional enrichments, not the product core.

---

# 23. Migration policy

Do not rewrite old Alembic migrations.

Add new forward migrations.

For local development it is acceptable to use:

```bash
make db-reset
```

because this is a single-user project and V2 may still be in dogfood mode.

But the migration chain itself should remain valid from Phase 1 → V2.

---

# 24. Testing rules

The budget system must be highly testable without an LLM.

All important finance logic should be pure or service-level Python.

At minimum test:

- exact week start/end
- exact month start/end
- JPY handling
- positive income excluded from spend
- spending category aggregation
- aggregate adjustment behavior
- set-total creates correct delta
- zero-spend categories
- over-budget category
- weekly/monthly plans coexisting
- cloning does not copy actual spending
- projection with zero elapsed days
- projection with final day
- future plan has zero actual spend
- transactions outside period excluded

Do not make LLM calls in these tests.

---

# 25. Completion criteria for V2 Phase 1

Call Phase 1 complete only when all of the following work end-to-end:

- [ ] I can create a monthly plan.
- [ ] I can assign category budgets.
- [ ] I can create a weekly plan separately.
- [ ] Dashboard switches between week and month.
- [ ] Each category shows planned / spent / remaining / state.
- [ ] I can add a quick expense without entering a merchant.
- [ ] Existing receipt import still creates spend that appears in the budget.
- [ ] I can set a category's current-period total using an adjustment.
- [ ] I can clone last week's plan into next week.
- [ ] Dashboard shows projected end-of-period spend.
- [ ] Existing Records / Import / Categories / Settings routes still work.
- [ ] Existing tests still pass.
- [ ] New budget tests pass.
- [ ] Visual style still matches MITA Finance's current warm-paper design.

---

# 26. Coding-agent execution instruction

When implementing this plan:

1. First inspect the existing repo before editing.
2. Reuse current architecture and naming conventions.
3. Write a short implementation plan before code changes.
4. Implement backend schema + services before wiring the new dashboard.
5. Add tests as each domain function lands.
6. Do not silently change unrelated Phase-1 behavior.
7. Prefer small, reviewable commits.
8. Update README and design docs after implementation.
9. Maintain a dev log under `docs/dev_log/`.
10. Do not proceed into V2 Phase 2 agent work during the same coding session.

The deliverable for this coding session is **V2 Phase 1: Budget Core**, not the entire future roadmap.

---

# 27. Product north star

MITA Finance V2 should feel less like:

> “A database that happens to contain my spending.”

and more like:

> “A personal spending control panel that knows what I planned, knows roughly what I spent, and helps me decide what to do next.”

The transaction ledger is infrastructure.

The budget state is the product.

The agent is the control layer.
