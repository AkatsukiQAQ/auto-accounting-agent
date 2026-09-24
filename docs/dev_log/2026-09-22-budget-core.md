# 2026-09-22 — V2 Phase 1 Budget Core

## Scope and starting state

Read the complete `design/V2_PRODUCT.md` and inspected schema, all relevant services/routes/DTOs, ledger/import integration, frontend hooks/primitives/pages, test fixtures and migration chain before implementation. Starting checkout was `main` at `8c7934d` with only initial tracked files; full project and product specification existed on `feature/basic_frontend` at `b7597b6`. Created `codex/v2-budget-core` from that branch, preserving untracked local data. No commits created in this task.

The grouped implementation plan and conflicts are recorded in `design/V2_PHASE_1_BUDGET_CORE.md`. Work stops at deterministic Budget Core. No V2 agent/chat implementation was added.

## Changes and decisions

- Added budget plans/items, forward migration `0006_budget_core`, nullable merchant and granularity. Reused existing source/note; preserved `photo` imports and all old migrations.
- Added week/month helpers, timezone-aware period boundaries, SQL aggregation, status, straight-line projection, plan/item CRUD, clone, quick expenses and signed set-total corrections. All money remains integer cents using the existing ×100 convention, including JPY.
- Ordinary income and transfer legs are excluded. Positive adjustment records reduce spending. Unbudgeted category spend is included in totals. Week and month share evidence; clones copy only allocations/targets.
- Kept existing ledger write cascade/default Cash compatibility. New aware timestamps normalize to UTC before SQLite strips offsets; output timestamps are explicitly UTC. Historical stored values are not rewritten.
- Dashboard now prioritizes budget KPIs, risk-sorted/groupable category cards, remaining daily allowance, deterministic pace observation and lower-priority recent records. Added Plan, period controls, merchant-free quick input and category-total adjustment UI; transaction/settings changes invalidate budget queries.
- Kept MITA layout, paper tokens and reusable components. Preserved Import/Records/Categories/Settings. Records clearly marks adjustments and permits deletion through existing flow.
- Added `tzdata` because Windows did not provide IANA timezone data; updated `uv.lock`.
- Fixed a pre-existing blocker discovered with an actually migrated empty database: migration 0004's transfer-only category table suppressed initial category seeds and broke startup under foreign keys. The seeder now recognizes that exact state; a fresh-database startup regression test covers it. No old migrations changed.
- Archived snapshots of the four requested V1 planning docs without breaking original links. Added Phase 1 behavior/API documentation and a Phase 2 deferred marker; refreshed README.

## Verification

Final backend command:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=.test-tmp-budget-elevated --tb=short
```

**245 passed**, 5 existing Alembic `path_separator` deprecation warnings. Original suite had 221 tests; 24 new cases cover period boundaries/DST, currency/JPY/income/transfers, deltas and no-ops, status/projection, future plans, clone behavior, validation, API CRUD, import-to-budget flow, UTC offsets, forward migration preservation and fresh migrated DB startup. No live LLM calls.

Frontend:

- `npm test`: **4 passed** (week/month navigation, exact input conversion, profile-zone date format).
- `npm run build`: **passed**, TypeScript and Vite production bundle.
- Targeted ESLint over all changed TS/TSX files: **passed**.
- Whole-repository `npm run lint`: **pre-existing** errors in `components/charts/DonutChart.tsx` (`react-refresh/only-export-components`) and `pages/ImportPage.tsx` (`prefer-const`), plus existing warnings in ErrorBoundary/ImportPage. Those files were not modified.
- `git diff --check`: passed.

The sandbox blocked pytest temporary directories and Node child processes (`PermissionError` / `spawn EPERM`). Tests/build were rerun with normal process permissions; these were environment issues, not test skips.

Browser smoke used an isolated SQLite database under `.test-tmp-budget-ui`, API port 18000 and frontend port 5174:

1. Created September monthly plan; saved JPY 300,000 income / 50,000 savings and Food 45,000 allocation.
2. Added merchant-free Food expense JPY 39,000; Dashboard immediately showed spent 39,000, remaining 6,000, warning, 87% used, 18% ahead of pace and projected 53,182.
3. Set Food total to JPY 21,000; Records displayed a positive 18,000 aggregate adjustment and retained the original expense.
4. Created an independent weekly plan, allocated Food 12,000, cloned Sep 21–27 into Sep 28–Oct 4; confirmed allocation persisted and future actual spending was zero.
5. Verified current Week/Month navigation, Records, Import, Categories and Settings render. Inspected Dashboard screenshot to confirm warm-paper styling and retained typography/primitives; styled native progress to match ink/paper tokens.

The existing `mita.db` was not migrated or modified. Development test servers are stopped at task completion.

## Remaining scope / next task

The requested Phase 1 vertical slice is implemented. Plan deletion is API-only; allocation removal is available in the UI. Automated reconciliation, exchange-rate conversion, agent/chat, slash commands and AI recommendations are intentionally absent. Historical timestamps whose offsets were previously discarded cannot be reconstructed automatically.

Suggested commit: `feat: add V2 budget core and budget-first dashboard`.

Suggested next task: apply the forward migration to a backed-up development DB and dogfood a real week/month, focusing on coarse adjustments followed by detailed imports and timezone boundaries. Do not start Phase 2 automatically.
