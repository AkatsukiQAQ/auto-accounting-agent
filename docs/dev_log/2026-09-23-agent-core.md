# 2026-09-23 — V2 Phase 2 Agent Core

## Scope and preserved work

Read `design/V2_PRODUCT.md` and inspected the existing budget mutations/summary/periods,
ledger service, schemas, routes, React Query hooks and UI before implementation.
The user's separately authorized Agent Core request supersedes the old Phase 2 deferred
marker. Existing uncommitted Phase 1 category/icons/localization/Dashboard changes were
preserved. No budget model redesign, receipt pipeline changes or agent hierarchy.

## Delivered

- Forward migration `0008_agent_core`: chat sessions, visible messages, structured action audit.
- Isolated single-agent module with typed read/write contracts, eight-step bounded model loop,
  latest twelve messages/eight actions, independent `AGENT_MODEL`, existing Settings key.
- Six read tools, six proposed-write tools, deterministic slash commands before model creation.
- `/spend`, `/income`, `/budget`, `/set-spent`, `/summary`, `/undo`.
- Apply/Cancel API with atomic status claim, service validation, stale-proposal checks,
  savepoint rollback on failure, repeated/concurrent confirmation idempotency and audit.
- Conservative undo through the same ledger/budget services. Refuses to destroy entries/items
  edited since execution. Whole-plan creation/clone and no-op adjustments are unsupported undo cases.
- Global paper-style ChatPanel, session recovery, inline proposal/result cards, category/date/currency
  previews, prior values, next-period Dashboard link, cache invalidation for budgets/transactions/accounts.
- NDJSON tool-progress stream and committed final response. Provider text-token streaming remains deferred.
- Moved the development-only Query Devtools launcher away from the Chat Send button.
- README, environment example and Phase 2 implementation/API/demo documentation updated.

## Validation

- Full backend: `python -m pytest -q -p no:cacheprovider --basetemp=.test-tmp-agent-final --tb=short`
  **298 passed**, nine existing Alembic `path_separator` deprecation warnings.
- Includes parser/malformed input, JPY/USD, typed reads, write validation, no pre-confirmation
  write calls, cancellation, exactly-once replay, real-file SQLite concurrent Apply, stale proposal,
  supported/refused undo, ledger/dashboard state, model/provider stubs and forward/reverse migrations.
- Frontend `npm test`: **8 passed**.
- Frontend `npm run build`: **passed** (TypeScript and Vite production build).
- Focused ESLint on ChatPanel, AppShell, api.ts, chat.ts and main.tsx: **passed**.
- Full ESLint: **3 pre-existing errors and 2 warnings**, in untouched DonutChart, locale,
  ImportPage and ErrorBoundary; not expanded into unrelated cleanup.
- `git diff --check`: **passed**.
- No paid model requests. Unit/API tests stub the model and provider.

Browser acceptance used a disposable in-memory database at localhost:18765 and a separate
Vite instance, not the user's real ledger:

1. Current-month question calls current plan and summary and shows Dining as over budget.
2. Natural-language next-week Dining ¥12,000 produces a pending card with Sep 28–Oct 4,
   category, currency and amount; Apply creates the plan using Budget Core.
3. View budget shows Dashboard Dining ¥0 / ¥12,000 for next week.
4. A later ¥8,000 proposal shows the previous ¥12,000 value; Cancel leaves the budget unchanged.
5. Refresh restores the same chat and action states.
6. `/spend 1800 dining` immediately updates current-month Dashboard from ¥11,000 to ¥12,800.
7. `/undo` returns Dashboard spending to ¥11,000 and marks the entry action undone.
8. Visual screenshot check confirmed the warm-paper panel and accessible controls.

## Operational notes and remaining work

Run `uv run alembic upgrade head` against the real application database before using Chat.
The actual user database was not reset or used for acceptance testing. The initial test/build
attempt hit Windows sandbox temp-directory/esbuild restrictions; after usage reset, approved
runs completed successfully.

Default categories include Food, so the exact Dining demo assumes a user-created Dining
category. Unknown categories are rejected, not silently remapped. Amounts remain hundredths
for every currency including JPY. `/income` is actual positive income, not planned income.

This slice deliberately supports one proposed write per message. Remaining Phase 2 work:
provider token streaming, richer multi-operation/recovery planning, optional proposal editing,
whole-plan undo and longer-history UX. Slash-message transport retries are not idempotent;
after a disconnect the user should refresh history before resending a slash mutation.
