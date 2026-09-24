from datetime import timedelta

import pytest

from backend.db.models import BudgetPlan
from backend.services.agent import planning
from backend.services.budget import mutations as budget
from backend.services.budget.periods import period_bounds
from backend.services.budget.summary import profile_context
from backend.services.errors import ConflictError, ValidationError


def weekly_plan(session, starts_on, *, income=10000000):
    plan = budget.create_plan(session, period_type="week", starts_on=starts_on,
                              currency="JPY", planned_income_cents=income)
    budget.add_item(session, plan.id, category_id="rent", limit_cents=5000000, kind="fixed")
    budget.add_item(session, plan.id, category_id="food", limit_cents=2000000, kind="flexible")
    budget.add_item(session, plan.id, category_id="shopping", limit_cents=1000000, kind="discretionary")
    return plan


def next_week(session):
    today = profile_context(session)[2]
    current_start, current_end = period_bounds("week", today)
    return current_start, current_end + timedelta(days=1)


def proposal_args(target_start, **overrides):
    result = {
        "target_starts_on": str(target_start),
        "summary": "Tighten flexible spending while preserving fixed costs.",
        "operations": [
            {"category_id": "food", "proposed_limit_cents": 1500000,
             "reason": "Recent weekly spending supports a lower cap."},
            {"category_id": "shopping", "proposed_limit_cents": 500000,
             "reason": "Reduce discretionary spending."},
        ],
    }
    result.update(overrides)
    return result


def test_planning_context_uses_four_completed_weeks(session):
    current_start, _ = next_week(session)
    weekly_plan(session, current_start)
    month_start, _ = period_bounds("month", profile_context(session)[2])
    monthly = budget.create_plan(session, period_type="month", starts_on=month_start,
                                 currency="JPY", planned_income_cents=30000000,
                                 savings_target_cents=5000000)
    budget.add_item(session, monthly.id, category_id="food", limit_cents=8000000)
    for offset in range(1, 5):
        start = current_start - timedelta(days=7 * offset)
        weekly_plan(session, start)
        budget.quick_expense(session, amount_cents=offset * 100000, category_id="food",
                             currency="JPY", occurred_on=start + timedelta(days=2))
    context = planning.get_context(session)
    assert context["available_history_weeks"] == 4
    assert len(context["completed_weeks"]) == 4
    assert [week["actual_spend_cents"] for week in context["completed_weeks"]] == [100000, 200000, 300000, 400000]
    assert all(week["summary"]["planned_spend_cents"] == 8000000 for week in context["completed_weeks"])
    assert context["baseline_plan"]["starts_on"] == str(current_start)
    assert context["target_period"]["starts_on"] == str(current_start + timedelta(days=7))
    assert context["monthly_summary"]["planned_income_cents"] == 30000000
    assert context["monthly_summary"]["savings_target_cents"] == 5000000


def test_planning_context_handles_insufficient_history(session):
    current_start, _ = next_week(session)
    weekly_plan(session, current_start)
    context = planning.get_context(session)
    assert context["available_history_weeks"] == 0
    assert len(context["completed_weeks"]) == 4
    assert all(week["summary"] is None for week in context["completed_weeks"])


def test_proposal_totals_constraints_and_fixed_preservation(session):
    current_start, target_start = next_week(session)
    weekly_plan(session, current_start)
    args, preview, _ = planning.prepare(session, proposal_args(target_start,
        planned_income_cents=10000000, savings_target_cents=2000000))
    assert args["target_starts_on"] == str(target_start)
    operations = {item["category_id"]: item for item in preview["operations"]}
    assert operations["rent"]["proposed_limit_cents"] == 5000000
    assert operations["rent"]["delta_cents"] == 0
    assert operations["food"]["delta_cents"] == -500000
    assert preview["totals"] == {
        "previous_planned_spend_cents": 8000000,
        "proposed_planned_spend_cents": 7000000,
        "planned_income_cents": 10000000,
        "savings_target_cents": 2000000,
        "projected_residual_cents": 3000000,
    }
    with pytest.raises(ValidationError, match="Fixed category rent"):
        planning.prepare(session, proposal_args(target_start, operations=[{
            "category_id": "rent", "proposed_limit_cents": 4000000,
            "reason": "Lower it", "allow_fixed_reduction": False,
        }]))
    _, allowed, _ = planning.prepare(session, proposal_args(target_start, operations=[{
        "category_id": "rent", "proposed_limit_cents": 4000000,
        "reason": "The user explicitly requested a temporary rent reduction.",
        "allow_fixed_reduction": True,
    }]))
    assert next(item for item in allowed["operations"] if item["category_id"] == "rent")["delta_cents"] == -1000000
    with pytest.raises(ValidationError, match="cannot meet"):
        planning.prepare(session, proposal_args(target_start,
            planned_income_cents=7000000, savings_target_cents=1000000))


def test_apply_and_undo_new_plan_as_one_action(session):
    current_start, target_start = next_week(session)
    weekly_plan(session, current_start)
    args, _, _ = planning.prepare(session, proposal_args(target_start))
    assert budget.list_plans(session, period_type="week", start=target_start, end=target_start, currency="JPY") == []
    result, inverse = planning.apply_proposal(session, args)
    assert result["summary"]["planned_spend_cents"] == 7000000
    assert len(result["plan"]["items"]) == 3
    planning.undo_proposal(session, inverse)
    assert budget.list_plans(session, period_type="week", start=target_start, end=target_start, currency="JPY") == []


def test_apply_and_undo_existing_plan_restores_limits(session):
    current_start, target_start = next_week(session)
    weekly_plan(session, current_start)
    target = weekly_plan(session, target_start, income=9000000)
    original = planning._plan_snapshot(target)
    args, _, _ = planning.prepare(session, proposal_args(target_start,
        planned_income_cents=9500000,
        operations=[{"category_id": "food", "proposed_limit_cents": 1200000,
                     "reason": "Explicit food cap"}]))
    _, inverse = planning.apply_proposal(session, args)
    planning.undo_proposal(session, inverse)
    assert planning._plan_snapshot(budget.get_plan(session, target.id)) == original


def test_stale_basis_includes_recent_spending(session):
    current_start, target_start = next_week(session)
    weekly_plan(session, current_start)
    args, _, before = planning.prepare(session, proposal_args(target_start))
    previous = current_start - timedelta(days=7)
    budget.quick_expense(session, amount_cents=100000, category_id="food",
                         currency="JPY", occurred_on=previous)
    assert planning.before_state(session, args) != before


def test_target_week_and_jpy_validation(session):
    current_start, target_start = next_week(session)
    weekly_plan(session, current_start)
    with pytest.raises(ValidationError, match="next Monday"):
        planning.prepare(session, proposal_args(current_start))
    with pytest.raises(ValidationError, match="whole currency units"):
        planning.prepare(session, proposal_args(target_start, operations=[{
            "category_id": "food", "proposed_limit_cents": 120001,
            "reason": "Fractional yen is invalid",
        }]))
