# V2 Phase 2 — Agent Core, first vertical slice

Implemented on the stable V2 Phase 1 budget services. This milestone does not change the budget model or receipt pipeline.

## Architecture

One bounded tool-calling loop: model → Pydantic-validated tool → deterministic service → structured result → model. At most eight model steps per message, with the latest twelve messages and eight structured action statuses as context. No LangGraph, supervisors, specialist agents or background workers.

- `backend/services/agent/commands.py`: strict slash grammar and currency conversion.
- `tools.py`: typed read/write arguments and results; delegates finance operations to Budget Core and ledger services.
- `actions.py`: proposal validation, snapshots, confirmation, cancellation, audit and conservative undo.
- `orchestrator.py`: slash-first dispatch, conversation context and bounded tool loop.
- `model.py`: independent OpenAI adapter, configurable with `AGENT_MODEL`; uses the existing Settings API key. Receipt import continues using `LLM_MODEL`.
- `planning.py`: deterministic planning context, complete-plan normalization, totals, stale fingerprints, atomic apply and logical undo.
- `frontend/src/components/chat/ChatPanel.tsx`: global warm-paper panel, session recovery, inline action cards, Apply/Edit/Cancel and budget links.

All financial sums, comparisons, statuses, projections and period boundaries come from Python/SQL services. Integer `*_cents` fields retain Phase 1's hundredths convention, including JPY: **¥12,000 = 1,200,000 stored units**. Slash amounts are major units; JPY/KRW fractional major units are rejected. Currency is explicit in proposals/results and defaults to profile currency in commands and reads. Currency validation reuses the existing three-uppercase-letter domain contract; it does not introduce a new ISO currency catalog or exchange conversion.

## Persistence and API

Forward migration `0008_agent_core` follows `0007_category_icons` and adds `chat_sessions`, `chat_messages`, and `agent_actions`. Existing budgets and entries are preserved. Apply it with `uv run alembic upgrade head` before using Chat against an existing database.

Actions store structured arguments, a user-visible preview, relevant before-state, execution result, optional undo metadata, status and timestamps. No hidden reasoning is requested or persisted. Tool transcripts exist only in the in-process model loop; persistent chat messages contain user-visible text.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET / POST | `/api/chat/sessions` | List recent sessions / create a session |
| GET | `/api/chat/sessions/{id}` | Restore messages and current action statuses |
| POST | `/api/chat/sessions/{id}/messages` | Send `{content}` and receive committed result |
| POST | `/api/chat/sessions/{id}/stream` | Same operation with NDJSON tool-progress and completion events |
| POST | `/api/chat/sessions/{id}/actions/{actionId}` | `{decision: "apply"}` or `{decision: "cancel"}` |
| PATCH | `/api/chat/sessions/{id}/actions/{actionId}` | Edit a pending complete-plan proposal and recompute its preview |

JSON endpoints retain the `{data: ...}` envelope and existing error convention. The stream emits `tool`, `done` or `error` events; completion is emitted **after commit**. It streams tool progress, not provider text tokens. The client refreshes history even after errors/disconnects and invalidates `budgets`, `transactions`, and `accounts` query keys. It does not automatically retry mutating requests.

Chat stores an opaque selected session ID locally; conversation contents live in SQLite. This remains the existing local, single-user application and does not add authentication or multi-user ownership.

## Tools

Reads execute automatically:

- `get_current_plan(period_type)`
- `get_plan_summary(plan_id)`
- `get_spending_breakdown(from, to, currency?)`
- `compare_spending(period_a, period_b)` — each period has dates and optional currency; cross-currency comparisons are rejected.
- `get_category_history(category_id, periods=4, period_type="month")`
- `get_recent_entries(category_id?, limit=10)`
- `get_budget_planning_context(history_weeks=4)` — completed weekly plan/spend snapshots, current week/month context, categories, planned income and savings targets.

Natural-language write tools **only create proposals**:

- `set_budget_item_limit(category_id, limit_cents, currency, period_type, starts_on, plan_id?)` — can create the exact period's plan at Apply time if missing.
- `set_planned_income(plan_id, amount_cents)`
- `set_savings_target(plan_id, amount_cents)`
- `add_quick_expense(category_id, amount_cents, currency, occurred_on, note?)`
- `set_category_spend_total(plan_id, category_id, total_cents, note?)`
- `clone_budget_plan(source_plan_id, starts_on)`
- `propose_next_week_budget(...)` — creates one complete structured proposal; it does not write until Apply.

These call the same `budget.mutations` and `ledger.apply` functions as normal UI routes. `/income` uses the existing positive ledger-entry service; it adds actual income and does not change planned income.

## Confirmation and undo

- Text such as “Apply”, “yes” or a model tool call cannot execute a natural-language proposal. Only the explicit action endpoint executes it.
- No financial write service is called while proposing or cancelling.
- An atomic conditional status update claims a proposed action before reading/mutating finance state. Domain changes and action status commit together. Repeated/concurrent Apply requests return the same executed result without reapplying.
- Apply validates again. If an overwritten budget value or cloned source changed since preview, the action fails with a request for a fresh proposal. Service failures roll back financial changes and persist the failed action.
- Cancellation is idempotent. A cancelled/failed action cannot subsequently be applied. Action IDs are scoped to their chat session.
- `/undo` reverses the latest executed, not-yet-undone action in that session when supported: agent-created entries/adjustments, limits in pre-existing plans, planned income, savings targets. Entry/item fingerprints reject destructive undo after manual edits. Undo itself is audited and reverses account balances through the ledger service.
- A complete next-week proposal has one logical undo: it deletes the plan when Apply created it, or restores the exact prior plan/items when Apply updated it. A stale fingerprint prevents undo after later edits.
- Generic creation/clone actions and no-op adjustments are not automatically undone. `/undo` reports that limitation instead of skipping backwards to an unrelated action.
- Slash message delivery is not an idempotency protocol. After an uncertain connection failure, refresh the conversation before manually resending a slash write.

## Slash commands

Commands are parsed before constructing the model client and work without an API key:

```text
/spend <amount> <category>
/income <amount> [note]
/budget <category> <amount> [week|month|next-week|next-month]
/set-spent <category> <amount> [week|month]
/summary [week|month]
/plan next-week
/help
/undo
```

Default period is month. Use category IDs or exact case-insensitive labels; quote multi-word categories. Unknown/ambiguous categories, malformed amounts and extra parameters are rejected rather than sent to the LLM. Commands freeze dates using the profile timezone. `/set-spent` requires an active current plan and uses the existing signed adjustment service.

`/plan next-week` is the deliberate exception to direct slash execution: it enters the same model-assisted planning flow and still requires Apply. `/help` is fully deterministic and works without a configured model key.

## Completion demo

Use an existing `dining` category (or create Dining in Categories; the factory defaults have Food, so Dining is not silently remapped).

1. Create a current monthly plan with category limits and recorded spending.
2. Open Ask MITA anywhere and ask “How am I doing this month?” The agent reads the current plan and summary, then explains deterministic risk statuses.
3. Ask “Set next week's dining budget to ¥12,000.” Inspect category, currency, dates and amount in the proposal card. No budget has changed yet.
4. Click Apply. The action card becomes Applied. Click View budget to see the next-week Dashboard with ¥12,000 allocated; existing Dashboard queries also refresh immediately.
5. `/spend 1800 dining` immediately adds a JPY 1,800 expense with source `slash`, without a model call. `/undo` removes it through the ledger service and refreshes the Dashboard.

Tests use model/provider stubs exclusively. Browser acceptance used a disposable in-memory ledger and model stub, not the user's actual database or a paid model call.

## Complete next-week planning

For requests such as “Help me make a stricter budget for next week”, the orchestrator must first read `get_budget_planning_context(4)`. The service returns up to four completed weeks of plan limits and recorded spend, the current weekly and monthly summaries when present, the exact next-Monday boundary, all spending categories, planned income and savings targets. Insufficient history is represented explicitly; it is not fabricated.

The model supplies category amounts and short user-visible reasons. `planning.prepare` resolves exact categories, fills unchanged baseline categories, preserves fixed categories unless an explicit reduction flag and reason are supplied, validates the savings constraint, and computes every delta and total with integer money. The resulting audit record is a single composite action containing the complete preview and one before-state fingerprint. Hidden reasoning is neither requested nor stored.

The card shows each category's kind, previous/proposed limit, delta and reason, followed by proposed spend, previous plan, planned income, expected residual and savings target. Edit sends only structured category operations to the PATCH endpoint; the backend rebuilds and revalidates the preview. Apply claims the action once and writes the target plan plus all category items inside the same transaction. Any stale evidence or invalid operation rejects the entire Apply. Cancel writes nothing. Successful Apply invalidates budget queries and links directly to the target week's Dashboard.

Users may also revise a pending plan in natural language. The model receives recent structured action arguments, but preservation does not depend on model memory: the action service deterministically overlays newly mentioned categories onto the last canonical pending preview and carries forward omitted category limits, income and savings. When the replacement validates, the older pending plan is atomically marked cancelled with a `supersededBy` audit link. Its Apply endpoint then rejects it, leaving exactly one actionable plan in the conversation.

## Remaining Phase 2 work

Provider token streaming, guided constraint controls beyond amount editing, reusable planning preferences, richer recovery explanations and longer-history UX are follow-ups. Generic whole-plan clone undo remains conservative. No anomaly detection, autonomous workers, bank sync, recommendation notifications, ML forecasting or specialist agents were added.
