# V2 Phase 1 — Budget Core

Implemented from `V2_PRODUCT.md`. This phase has no chatbot, slash parser, agent tools, action log, recommendations, workers, bank sync or new accounts functionality.

## Repository comparison and implementation plan

- **Database:** keep transactions/categories/settings and the five existing migrations. Add budget plans/items and transaction granularity; make merchant nullable. Existing `source` and `note` are reused.
- **Backend:** retain FastAPI, SQLAlchemy sessions, service exceptions, route-owned commits and camelCase envelopes. Add period helpers, CRUD/clone, integer-money aggregation, status/projection and signed adjustment creation.
- **Frontend:** keep fetchJson, React Query, MITA tokens/primitives, Records/Import/Categories/Settings. Replace Dashboard hierarchy, add Plan, period navigation, quick expenses and set-total form. Invalidate budget summaries after transaction and settings writes.
- **Tests:** pure boundaries/status/projections, service aggregation/adjustments/clone/currencies, API integration, forward migrations, fresh-database startup, frontend money/date helpers, browser smoke.
- **Documentation:** preserve V1 planning snapshots, update README and this behavior contract, record verification in the development log. Phase 2 document is only a deferred-scope marker.

## Conflicts resolved

The supplied checkout was `main` at initial commit; the existing implementation and product spec were on `feature/basic_frontend`. Work is on `codex/v2-budget-core`, branched from that implementation.

The code already contains V1 accounts/transfers and merchant normalization. They remain unchanged except for skipping merchant normalization when no merchant was supplied. New transactions use the existing ledger writer and its default Cash account for backward compatibility. Transfers are excluded from spending. This phase adds no account UX or account features.

`source` and `note` already existed. Existing imported `photo` records keep their source and count in budgets. V2 source values are accepted without changing the import pipeline. All currencies retain the repository's major-unit ×100 storage convention: JPY 1,200 is 120000 cents.

Old migrations are unchanged. A fresh database previously failed startup because migration 0004's solitary `transfer` category suppressed first-boot category seeds; the seeder now recognizes that migration-only state. This narrowly scoped fix is required for a runnable fresh installation.

## Product and calculation rules

- One plan per period type/start/currency, regardless of status. Weeks are Monday–Sunday, months are calendar months. Creation rejects noncanonical dates. Period/currency are immutable; clone to move a plan.
- Income and savings targets are nullable nonnegative integer cents. Missing income is unknown, not zero. Residual = income − allocations; it can be positive or negative. Savings target is informational and does not double-count as an expense.
- Each category has one item per plan. Limits are nonnegative; kinds are fixed/flexible/discretionary, selected by the user. Warning ratio is configurable per item (default .80); service watch threshold defaults to .60.
- Aggregation runs in SQL across all matching records, with no pagination cutoff. Every negative non-transfer transaction counts. Ordinary positive income does not count. Adjustment-source amounts are signed: a positive adjustment reduces spend.
- Unallocated categories still count toward total spent/remaining and appear separately on Dashboard.
- Profile timezone defines boundaries; convert local midnight through next midnight to half-open UTC bounds, including DST. New aware transaction timestamps are normalized to UTC before SQLite storage and emitted with a UTC offset. Legacy naive timestamps retain their existing assumed-UTC interpretation; unavailable historical offsets are not guessed.
- Actual spend is through the end of `asOf` (inclusive), clamped to today in the profile timezone and plan end. Future plans show zero actual/projected spending, even if future-dated records exist. Quick expenses reject future dates.
- Elapsed days include today, clamped to 0…period length. Remaining days exclude today. Projection = actual × total days / elapsed days, rounding half-up to integer cents; zero elapsed gives zero, completed period gives actual.
- Status: `over` when spent > limit; `warning` when used ratio reaches item warning threshold and pace exceeds elapsed time; `watch` at watch threshold; otherwise `safe`. Zero limit produces a null ratio (no Infinity/NaN) and positive spending is `over`.
- Daily flexible allowance = nonnegative remaining flexible + discretionary budget, capped by overall remaining, divided by remaining days (floor to integer cents). No remaining days gives zero. It is an arithmetic indicator, not an AI recommendation.
- Set total computes desired − current and appends the opposite signed amount as `source=adjustment`, `granularity=aggregate_adjustment`, merchant null. No-op totals produce no record. The record is dated today or period end for a completed plan. Future-period adjustments are rejected. SQLite writer locking precedes the read to serialize competing corrections.
- Week and month views share transaction evidence: an adjustment dated in both periods affects both. No artificial ownership of spending by a plan.
- Cloning copies targets, notes and item allocations/thresholds/kinds with fresh IDs and `createdBy=template`. The clone starts active, retains currency/type, and copies no transactions. Existing target plans return conflict.
- Records displays aggregate adjustments and their notes; delete reverses their effect through the existing transaction deletion path. Later receipts are additive. No automatic reconciliation.

## API

All successful results use `{data: ...}` and existing error envelopes/status codes. Money inputs are strict integer cents, not decimal major units.

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET/POST | `/api/budget-plans` | List / create; list supports `periodType`, `from`, `to`, `currency` |
| GET/PATCH/DELETE | `/api/budget-plans/{id}` | Read / edit targets, note, status / delete allocations and plan |
| POST | `/api/budget-plans/{id}/clone` | `{startsOn, endsOn?}` |
| POST | `/api/budget-plans/{id}/items` | `{categoryId, limitCents, warningRatio?, kind?, note?}` |
| PATCH/DELETE | `/api/budget-items/{id}` | Edit allocation / remove |
| GET | `/api/budget-plans/{id}/summary` | Deterministic summary; optional `asOf` |
| GET | `/api/budget-summary/current` | Active plan summary or null; `periodType`, optional `onDate`, `currency` |
| POST | `/api/transactions/quick` | `{amountCents: positive, categoryId, currency, occurredOn, note?}` |
| POST | `/api/budget-spend/set-total` | `{planId, categoryId, totalCents: nonnegative, note?}`; transaction or null |

Dashboard/Plan use the selected period's plan, including draft/closed for historical inspection. The current-summary endpoint specifically selects active status. Plan deletion is available through the API; the UI removes allocations individually.

## Migration and validation

`0006_budget_core` follows `0005_merchants`, adds both budget tables with uniqueness/check/foreign-key constraints, adds transaction granularity defaulting to `transaction`, and makes merchant nullable. Source/note and historical values are preserved. Downgrade refuses to discard or invent merchants for merchant-less V2 records.

Tests cover boundary/DST/JPY behavior, income and transfer exclusion, currency isolation, signed corrections, missing allocations, cloning, future and completed periods, API errors, receipt import integration, and migration preservation. See the dev log for exact commands and results.

## Remaining limits

No automatic reconciliation of aggregate estimates and later detailed imports, no exchange-rate conversion, no historic timezone repair, and no AI forecasting. These are intentional boundaries. Browser smoke uses an isolated database; real receipt OCR is covered through the existing fake-LLM pipeline tests, without paid external calls.
