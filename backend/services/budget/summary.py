from datetime import datetime

from sqlalchemy import case, func, select

from backend.db.models import BudgetPlan, Transaction
from backend.services.settings import get_settings
from .mutations import get_plan
from .periods import elapsed_days, period_bounds, utc_bounds, zone
from .projections import item_status, project_spend


def profile_context(session):
    profile = get_settings(session).get("profile") or {}
    tz = profile.get("timezone") or "Asia/Tokyo"
    return tz, profile.get("defaultCurrency") or "JPY", datetime.now(zone(tz)).date()


def get_active_plan(session, period_type, on_date, currency):
    start, _ = period_bounds(period_type, on_date)
    return session.scalar(select(BudgetPlan).where(BudgetPlan.period_type == period_type,
        BudgetPlan.starts_on == start, BudgetPlan.currency == currency, BudgetPlan.status == "active"))


def spend_by_category(session, start, end, currency, timezone_name):
    if end < start:
        return {}
    low, high = utc_bounds(start, end, timezone_name)
    # Ordinary income is not negative spend. Signed corrections are: reducing
    # a previously estimated total must reduce spend without deleting history.
    amount = case((Transaction.source == "adjustment", -Transaction.amount_cents),
                  (Transaction.amount_cents < 0, -Transaction.amount_cents), else_=0)
    rows = session.execute(select(Transaction.category_id, func.sum(amount)).where(
        Transaction.occurred_at >= low, Transaction.occurred_at < high,
        Transaction.currency == currency, Transaction.type.not_in(("transfer_out", "transfer_in")),
        # A bad historical/manual sign on an income row must not turn income
        # into budget spend. Budget mutations already reject these categories;
        # keep imported and legacy rows equally safe.
        Transaction.category_id.not_in(("income", "transfer"))).group_by(Transaction.category_id))
    return {category: int(total) for category, total in rows}


def get_period_spend(session, category_id, start, end, currency, timezone_name="Asia/Tokyo"):
    return spend_by_category(session, start, end, currency, timezone_name).get(category_id, 0)


def get_plan_summary(session, plan_id, as_of=None, watch_ratio=0.6):
    plan = get_plan(session, plan_id)
    tz, _, today = profile_context(session)
    as_of = min(as_of or today, today)
    elapsed, remaining = elapsed_days(plan.starts_on, plan.ends_on, as_of)
    total = elapsed + remaining
    spend = spend_by_category(session, plan.starts_on, min(plan.ends_on, as_of), plan.currency, tz)
    items = []
    for item in plan.items:
        spent = spend.get(item.category_id, 0)
        used = spent / item.limit_cents if item.limit_cents else None
        items.append(dict(category_id=item.category_id, kind=item.kind, limit_cents=item.limit_cents,
                          spent_cents=spent, remaining_cents=item.limit_cents-spent, used_ratio=used,
                          pace_ratio=used * total / elapsed if elapsed and used is not None else None,
                          status=item_status(spent, item.limit_cents, elapsed, total, item.warning_ratio, watch_ratio)))
    ranks = {"over": 0, "warning": 1, "watch": 2, "safe": 3}
    items.sort(key=lambda i: (ranks[i["status"]], i["remaining_cents"], i["category_id"]))
    planned = sum(i.limit_cents for i in plan.items)
    actual = sum(spend.values())
    projected = project_spend(actual, elapsed, total)
    allocated = {i.category_id for i in plan.items}
    unbudgeted = [dict(category_id=k, spent_cents=v) for k, v in spend.items() if k not in allocated and v]
    flexible_remaining = sum(i["remaining_cents"] for i in items if i["kind"] != "fixed")
    return dict(plan_id=plan.id, currency=plan.currency, timezone=tz,
                period=dict(type=plan.period_type, starts_on=plan.starts_on, ends_on=plan.ends_on,
                            days_elapsed=elapsed, days_remaining=remaining),
                planned_income_cents=plan.planned_income_cents, savings_target_cents=plan.savings_target_cents,
                planned_spend_cents=planned, actual_spend_cents=actual, remaining_budget_cents=planned-actual,
                planned_residual_cents=None if plan.planned_income_cents is None else plan.planned_income_cents-planned,
                projected_spend_cents=projected,
                projected_savings_cents=None if plan.planned_income_cents is None else plan.planned_income_cents-projected,
                safe_daily_spend_cents=max(0, min(flexible_remaining, planned-actual)) // remaining if remaining else 0,
                items=items, unbudgeted=unbudgeted)
