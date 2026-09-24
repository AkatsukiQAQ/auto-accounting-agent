# 2026-09-24 — V2 Phase 2 Budget Planning Agent

## Scope

Extended the existing single-agent Chat vertical slice without changing the Phase 1 budget model, receipt pipeline, or service ownership. The new milestone reads deterministic weekly/monthly evidence and proposes one complete next-week budget with explicit confirmation.

## Delivered

- Added `backend/services/agent/planning.py` for four-week planning context, exact next-week boundaries, baseline selection, complete-plan normalization, fixed-category protection, income/savings checks, deterministic totals, stale fingerprints, composite Apply and logical undo.
- Added typed `get_budget_planning_context` and `propose_next_week_budget` tools. The orchestrator requires the context read before accepting a plan proposal.
- Reused `agent_actions` for one structured composite proposal and result. No hidden reasoning is stored and no schema migration was needed.
- Added PATCH editing for pending plan actions. Each edit reruns domain validation and recalculates the server-authored preview.
- Added a warm-paper plan card with all categories, kind, previous/proposed amount, delta, reason, planned spend, income, savings and residual, plus Apply/Edit/Cancel.
- Added deterministic `/help`, model-assisted `/plan next-week`, and empty-chat suggestion chips for status, planning, recent spending and command discovery.
- Added conversational plan revision. The service deterministically overlays mentioned categories on the last canonical preview and carries omitted category/income/savings values forward. A validated replacement cancels the older pending plan and stores `supersededBy`; the old card can no longer execute.
- Apply is an exactly-once transaction across the plan and all category items. Stale evidence or any invalid child operation leaves the budget unchanged. Cache invalidation refreshes the target week's Dashboard.
- `/undo` treats the proposal as one logical action: delete an agent-created target plan or restore the prior plan snapshot after conflict checks.

## Validation

- Full backend: `python -m pytest -q -p no:cacheprovider --tb=short` — **317 passed**, with nine existing Alembic configuration deprecation warnings.
- Planning/chat focused suite — **32 passed**. Coverage includes four completed weeks, insufficient history, fixed preservation and explicit override, savings constraints, multiple child operations, deterministic totals, no pre-confirmation mutation, edit, cancellation, exactly-once Apply, atomic rollback, stale rejection, whole-plan undo, week boundaries and JPY whole-unit validation.
- Frontend `npm test` — **9 passed**.
- Frontend `npm run build` — **passed**.
- Focused ESLint for the changed Chat and app-shell files — **passed**.
- `git diff --check` — **passed**.
- All LLM behavior used stubs; no paid model requests.

Browser acceptance used a disposable in-memory database and model stub. A four-week history produced a complete proposal with Rent preserved, Food and Shopping reduced. Editing Food from ¥15,000 to ¥12,000 recalculated the plan from ¥70,000 to ¥67,000 and the residual from ¥30,000 to ¥33,000. Apply showed Rent ¥50,000, Food ¥12,000 and Shopping ¥5,000 on the target-week Dashboard. `/undo` removed the newly created plan and restored the Dashboard's empty state.

A second isolated browser pass verified the new suggestion chips, `/help` without a model call, `/plan next-week`, and natural-language replacement. The original ¥70,000 pending card became “Replaced by a newer proposal”; the new Food ¥12,000 proposal showed ¥67,000 planned spend and ¥33,000 residual with Apply/Edit/Cancel available.

## Remaining Phase 2 work

Provider text-token streaming, richer guided constraints/preferences, longer-history exploration and recovery-oriented explanations remain. Autonomous workers, anomaly detection, bank sync, notifications, forecasting ML and specialist-agent routing stay outside this milestone.
