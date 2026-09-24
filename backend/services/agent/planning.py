"""Deterministic context, proposal math, atomic apply and logical undo for weekly plans."""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError as PydanticError
from sqlalchemy import select

from backend.api.schemas.budget import SummaryOut
from backend.db.models import BudgetPlan, Category
from backend.services.budget import mutations as budget, summary
from backend.services.budget.periods import period_bounds
from backend.services.errors import ConflictError, ValidationError
from backend.services.transactions import _validate_currency

Money = Annotated[StrictInt, Field(ge=0, le=9_007_199_254_740_991)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningContextInput(Input):
    history_weeks: int = Field(default=4, ge=1, le=8)


class PlanOperation(Input):
    category_id: str
    proposed_limit_cents: Money
    reason: str = Field(min_length=1, max_length=500)
    allow_fixed_reduction: bool = False


class PlanProposalInput(Input):
    target_starts_on: date
    summary: str = Field(min_length=1, max_length=1000)
    operations: list[PlanOperation] = Field(min_length=1, max_length=100)
    planned_income_cents: Money | None = None
    savings_target_cents: Money | None = None


def _plan_for(session, starts_on: date, currency: str) -> BudgetPlan | None:
    return session.scalar(select(BudgetPlan).where(
        BudgetPlan.period_type == "week", BudgetPlan.starts_on == starts_on,
        BudgetPlan.currency == currency,
    ))


def _plan_snapshot(plan: BudgetPlan | None) -> dict | None:
    if plan is None:
        return None
    return {
        "id": plan.id,
        "starts_on": str(plan.starts_on),
        "ends_on": str(plan.ends_on),
        "currency": plan.currency,
        "status": plan.status,
        "note": plan.note,
        "created_by": plan.created_by,
        "planned_income_cents": plan.planned_income_cents,
        "savings_target_cents": plan.savings_target_cents,
        "items": [{
            "id": item.id,
            "category_id": item.category_id,
            "limit_cents": item.limit_cents,
            "warning_ratio": item.warning_ratio,
            "kind": item.kind,
            "note": item.note,
        } for item in plan.items],
    }


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def get_context(session, history_weeks: int = 4) -> dict:
    """Return complete, service-computed evidence for one next-week planning decision."""
    if not 1 <= history_weeks <= 8:
        raise ValidationError("historyWeeks must be between 1 and 8")
    timezone_name, currency, today = summary.profile_context(session)
    current_start, current_end = period_bounds("week", today)
    target_start, target_end = period_bounds("week", current_end + timedelta(days=1))
    current = _plan_for(session, current_start, currency)
    target = _plan_for(session, target_start, currency)

    completed = []
    for offset in range(1, history_weeks + 1):
        start = current_start - timedelta(days=7 * offset)
        end = start + timedelta(days=6)
        plan = _plan_for(session, start, currency)
        spend = summary.spend_by_category(session, start, end, currency, timezone_name)
        completed.append({
            "starts_on": str(start), "ends_on": str(end),
            "plan": _plan_snapshot(plan),
            "summary": SummaryOut.model_validate(summary.get_plan_summary(session, plan.id, end)).model_dump(mode="json") if plan else None,
            "spending_by_category": spend,
            "actual_spend_cents": sum(spend.values()),
        })

    monthly = summary.get_active_plan(session, "month", today, currency)
    baseline = target or current or next((
        _plan_for(session, date.fromisoformat(week["starts_on"]), currency)
        for week in completed if week["plan"] is not None
    ), None)
    categories = [{"id": row.id, "label": row.label} for row in session.scalars(
        select(Category).order_by(Category.sort_order, Category.id)
    ) if row.id not in budget.NON_SPENDING_CATEGORY_IDS]
    return {
        "today": str(today), "timezone": timezone_name, "currency": currency,
        "target_period": {"period_type": "week", "starts_on": str(target_start), "ends_on": str(target_end)},
        "target_plan": _plan_snapshot(target),
        "baseline_plan": _plan_snapshot(baseline),
        "current_week": {
            "starts_on": str(current_start), "ends_on": str(current_end),
            "plan": _plan_snapshot(current),
            "summary": SummaryOut.model_validate(summary.get_plan_summary(session, current.id)).model_dump(mode="json") if current else None,
        },
        "completed_weeks": completed,
        "available_history_weeks": sum(1 for week in completed if week["plan"] is not None or week["actual_spend_cents"] > 0),
        "monthly_plan": _plan_snapshot(monthly),
        "monthly_summary": SummaryOut.model_validate(summary.get_plan_summary(session, monthly.id)).model_dump(mode="json") if monthly else None,
        "categories": categories,
    }


def _validated_input(args: dict) -> PlanProposalInput:
    try:
        return PlanProposalInput.model_validate(args)
    except PydanticError as exc:
        raise ValidationError(str(exc)) from exc


def _basis(context: dict) -> dict:
    return {
        "target_period": context["target_period"],
        "target_plan": context["target_plan"],
        "baseline_plan": context["baseline_plan"],
        "current_week": context["current_week"],
        "completed_weeks": context["completed_weeks"],
        "monthly_plan": context["monthly_plan"],
        "monthly_summary": context["monthly_summary"],
    }


def prepare(session, raw_args: dict) -> tuple[dict, dict, dict]:
    """Canonicalize a partial model proposal into a complete, deterministic plan."""
    proposal = _validated_input(raw_args)
    context = get_context(session)
    target = context["target_period"]
    if proposal.target_starts_on != date.fromisoformat(target["starts_on"]):
        raise ValidationError("A next-week plan must target the next Monday shown in planning context")
    _validate_currency(context["currency"])
    if context["currency"] in ("JPY", "KRW"):
        money_values = [operation.proposed_limit_cents for operation in proposal.operations]
        money_values += [value for value in (proposal.planned_income_cents, proposal.savings_target_cents) if value is not None]
        if any(value % 100 for value in money_values):
            raise ValidationError(f"{context['currency']} requires whole currency units")

    baseline = context["baseline_plan"]
    baseline_items = {item["category_id"]: item for item in (baseline or {}).get("items", [])}
    operations_by_category: dict[str, PlanOperation] = {}
    for operation in proposal.operations:
        if operation.category_id in operations_by_category:
            raise ValidationError(f"Duplicate category in plan proposal: {operation.category_id}")
        budget.validate_item(session, operation.category_id, operation.proposed_limit_cents, .8, "flexible")
        operations_by_category[operation.category_id] = operation

    all_ids = list(baseline_items)
    all_ids.extend(category_id for category_id in operations_by_category if category_id not in baseline_items)
    canonical = []
    for category_id in all_ids:
        previous = baseline_items.get(category_id)
        requested = operations_by_category.get(category_id)
        proposed = requested.proposed_limit_cents if requested else previous["limit_cents"]
        kind = previous["kind"] if previous else "flexible"
        if previous and kind == "fixed" and proposed < previous["limit_cents"]:
            if not requested or not requested.allow_fixed_reduction:
                raise ValidationError(f"Fixed category {category_id} cannot be reduced without explicit justification")
        canonical.append({
            "category_id": category_id,
            "kind": kind,
            "warning_ratio": previous["warning_ratio"] if previous else .8,
            "note": previous["note"] if previous else None,
            "previous_limit_cents": previous["limit_cents"] if previous else 0,
            "proposed_limit_cents": proposed,
            "delta_cents": proposed - (previous["limit_cents"] if previous else 0),
            "reason": requested.reason if requested else "Preserved from the baseline weekly plan.",
            "allow_fixed_reduction": requested.allow_fixed_reduction if requested else False,
        })
    if not canonical:
        raise ValidationError("A budget plan proposal must contain at least one spending category")

    planned_income = proposal.planned_income_cents
    savings_target = proposal.savings_target_cents
    if planned_income is None and baseline:
        planned_income = baseline["planned_income_cents"]
    if savings_target is None and baseline:
        savings_target = baseline["savings_target_cents"]
    previous_total = sum(item["limit_cents"] for item in (baseline or {}).get("items", []))
    proposed_total = sum(item["proposed_limit_cents"] for item in canonical)
    projected_residual = None if planned_income is None else planned_income - proposed_total
    if savings_target is not None and projected_residual is not None and projected_residual < savings_target:
        raise ValidationError("The proposed plan cannot meet its savings target with the available planned income")

    normalized_args = proposal.model_dump(mode="json")
    preview = {
        "type": "budget_plan_proposal",
        "target_period": target,
        "currency": context["currency"],
        "summary": proposal.summary,
        "operations": canonical,
        "totals": {
            "previous_planned_spend_cents": previous_total,
            "proposed_planned_spend_cents": proposed_total,
            "planned_income_cents": planned_income,
            "savings_target_cents": savings_target,
            "projected_residual_cents": projected_residual,
        },
        "history_weeks_used": context["available_history_weeks"],
    }
    basis = _basis(context)
    before = {"basis_fingerprint": _hash(basis), "target_plan": context["target_plan"]}
    return normalized_args, preview, before


def before_state(session, _args: dict) -> dict:
    context = get_context(session)
    return {"basis_fingerprint": _hash(_basis(context)), "target_plan": context["target_plan"]}


def apply_proposal(session, args: dict) -> tuple[dict, dict]:
    _, preview, _ = prepare(session, args)
    target_start = date.fromisoformat(preview["target_period"]["starts_on"])
    currency = preview["currency"]
    totals = preview["totals"]
    target = _plan_for(session, target_start, currency)
    before = _plan_snapshot(target)
    if target is None:
        target = budget.create_plan(
            session, period_type="week", starts_on=target_start, currency=currency,
            planned_income_cents=totals["planned_income_cents"],
            savings_target_cents=totals["savings_target_cents"], created_by="agent",
            note="Created from a confirmed MITA weekly plan proposal.",
        )
    else:
        budget.update_plan(session, target.id,
            planned_income_cents=totals["planned_income_cents"],
            savings_target_cents=totals["savings_target_cents"])
    existing = {item.category_id: item for item in target.items}
    for operation in preview["operations"]:
        item = existing.get(operation["category_id"])
        if item:
            budget.update_item(session, item.id, limit_cents=operation["proposed_limit_cents"])
        else:
            budget.add_item(session, target.id, category_id=operation["category_id"],
                limit_cents=operation["proposed_limit_cents"],
                warning_ratio=operation["warning_ratio"], kind=operation["kind"], note=operation["note"])
    after = _plan_snapshot(target)
    result = {"plan": after, "summary": SummaryOut.model_validate(
        summary.get_plan_summary(session, target.id)).model_dump(mode="json")}
    return result, {"kind": "budget_plan", "plan_id": target.id, "before": before, "after": after}


def undo_proposal(session, inverse: dict) -> None:
    plan = budget.get_plan(session, inverse["plan_id"])
    if _plan_snapshot(plan) != inverse["after"]:
        raise ConflictError("Budget plan changed since this action; automatic undo is unsafe")
    before = inverse["before"]
    if before is None:
        budget.delete_plan(session, plan.id)
        return
    budget.update_plan(session, plan.id,
        planned_income_cents=before["planned_income_cents"],
        savings_target_cents=before["savings_target_cents"],
        status=before["status"], note=before["note"])
    prior = {item["category_id"]: item for item in before["items"]}
    for item in list(plan.items):
        if item.category_id not in prior:
            budget.delete_item(session, item.id)
    current = {item.category_id: item for item in plan.items}
    for category_id, item_before in prior.items():
        item = current[category_id]
        budget.update_item(session, item.id, limit_cents=item_before["limit_cents"],
            warning_ratio=item_before["warning_ratio"], kind=item_before["kind"], note=item_before["note"])
