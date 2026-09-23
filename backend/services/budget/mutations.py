from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.db.models import BudgetItem, BudgetPlan, Category
from backend.services.errors import ConflictError, NotFoundError, ValidationError
from backend.services.ids import new_budget_id
from backend.services.ledger import apply
from backend.services.transactions import _validate_currency
from .periods import period_bounds, zone


def money(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not int or not 0 <= value <= 9_007_199_254_740_991:
        raise ValidationError("Money must be a non-negative safe integer in cents")


def flush_unique(session):
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError("A budget already exists for this period/currency or category") from exc


def get_plan(session: Session, plan_id: str) -> BudgetPlan:
    plan = session.get(BudgetPlan, plan_id)
    if plan is None:
        raise NotFoundError("Budget plan not found")
    return plan


def list_plans(session, *, period_type=None, start=None, end=None, currency=None):
    stmt = select(BudgetPlan)
    if period_type:
        period_bounds(period_type, date.today())
        stmt = stmt.where(BudgetPlan.period_type == period_type)
    if start:
        stmt = stmt.where(BudgetPlan.ends_on >= start)
    if end:
        stmt = stmt.where(BudgetPlan.starts_on <= end)
    if currency:
        _validate_currency(currency)
        stmt = stmt.where(BudgetPlan.currency == currency)
    return list(session.scalars(stmt.order_by(BudgetPlan.starts_on.desc())))


def create_plan(session, *, period_type, starts_on, currency, ends_on=None,
                planned_income_cents=None, savings_target_cents=None, status="active", note=None,
                created_by="user"):
    start, end = period_bounds(period_type, starts_on)
    if starts_on != start or (ends_on is not None and ends_on != end):
        raise ValidationError("Plan dates must span a Monday–Sunday week or a calendar month")
    _validate_currency(currency)
    money(planned_income_cents, nullable=True)
    money(savings_target_cents, nullable=True)
    if status not in ("draft", "active", "closed") or created_by not in ("user", "template", "agent"):
        raise ValidationError("Invalid plan status or creator")
    if list_plans(session, period_type=period_type, start=start, end=end, currency=currency):
        raise ConflictError("A plan already exists for this period and currency")
    plan = BudgetPlan(id=new_budget_id(), period_type=period_type, starts_on=start, ends_on=end,
                      currency=currency, planned_income_cents=planned_income_cents,
                      savings_target_cents=savings_target_cents, status=status, note=note, created_by=created_by)
    session.add(plan)
    flush_unique(session)
    return plan


def update_plan(session, plan_id, **patch):
    plan = get_plan(session, plan_id)
    if set(patch) - {"planned_income_cents", "savings_target_cents", "status", "note"}:
        raise ValidationError("Period and currency are immutable; clone into a new period")
    for key in ("planned_income_cents", "savings_target_cents"):
        if key in patch:
            money(patch[key], nullable=True)
    if "status" in patch and patch["status"] not in ("draft", "active", "closed"):
        raise ValidationError("Invalid plan status")
    for key, value in patch.items():
        setattr(plan, key, value)
    session.flush()
    return plan


def delete_plan(session, plan_id):
    session.delete(get_plan(session, plan_id))
    session.flush()


def validate_item(session, category_id, limit_cents, warning_ratio, kind):
    if category_id == "transfer" or session.get(Category, category_id) is None:
        raise ValidationError("Select an existing spending category")
    money(limit_cents)
    if warning_ratio is None or not Decimal(0) < Decimal(str(warning_ratio)) <= Decimal(1):
        raise ValidationError("warningRatio must be greater than zero and at most one")
    if kind not in ("fixed", "flexible", "discretionary"):
        raise ValidationError("Invalid budget kind")


def add_item(session, plan_id, *, category_id, limit_cents, warning_ratio=0.8, kind="flexible", note=None):
    plan = get_plan(session, plan_id)
    validate_item(session, category_id, limit_cents, warning_ratio, kind)
    if any(item.category_id == category_id for item in plan.items):
        raise ConflictError("Category already allocated in this plan")
    item = BudgetItem(id=new_budget_id(), category_id=category_id, limit_cents=limit_cents,
                      warning_ratio=warning_ratio, kind=kind, note=note)
    plan.items.append(item)
    flush_unique(session)
    return item


def get_item(session, item_id):
    item = session.get(BudgetItem, item_id)
    if item is None:
        raise NotFoundError("Budget item not found")
    return item


def update_item(session, item_id, **patch):
    item = get_item(session, item_id)
    if set(patch) - {"limit_cents", "warning_ratio", "kind", "note"}:
        raise ValidationError("Unknown budget item fields")
    values = {k: patch.get(k, getattr(item, k)) for k in ("limit_cents", "warning_ratio", "kind")}
    validate_item(session, item.category_id, **values)
    for key, value in patch.items():
        setattr(item, key, value)
    session.flush()
    return item


def delete_item(session, item_id):
    item = get_item(session, item_id)
    plan = get_plan(session, item.plan_id)
    plan.items.remove(item)
    session.flush()


def clone_plan(session, source_plan_id, starts_on, ends_on=None):
    source = get_plan(session, source_plan_id)
    target = create_plan(session, period_type=source.period_type, starts_on=starts_on, ends_on=ends_on,
                         currency=source.currency, planned_income_cents=source.planned_income_cents,
                         savings_target_cents=source.savings_target_cents, note=source.note, created_by="template")
    for item in source.items:
        add_item(session, target.id, category_id=item.category_id, limit_cents=item.limit_cents,
                 warning_ratio=item.warning_ratio, kind=item.kind, note=item.note)
    return target


def quick_expense(session, *, amount_cents, category_id, currency, occurred_on, note=None):
    from .summary import profile_context
    money(amount_cents)
    if amount_cents == 0 or category_id == "transfer":
        raise ValidationError("Expense must be positive and use a spending category")
    tz, _, today = profile_context(session)
    if occurred_on > today:
        raise ValidationError("An actual expense cannot be in the future")
    when = datetime.combine(occurred_on, time(12), zone(tz)).astimezone(timezone.utc).replace(tzinfo=None)
    return apply.create(session, occurred_at=when, merchant=None, amount_cents=-amount_cents,
                        currency=currency, category_id=category_id, source="manual", granularity="quick", note=note)


def set_category_spend_total(session, *, plan_id, category_id, total_cents, note=None, as_of=None):
    from .summary import profile_context, spend_by_category
    plan = get_plan(session, plan_id)
    money(total_cents)
    if category_id == "transfer" or session.get(Category, category_id) is None:
        raise ValidationError("Select an existing spending category")
    tz, _, today = profile_context(session)
    today = as_of or today
    if today < plan.starts_on:
        raise ValidationError("Cannot adjust a future period")
    # Acquire SQLite's writer lock BEFORE reading the current total. Concurrent
    # set-total requests then compute their delta against the preceding commit.
    session.execute(update(BudgetPlan).where(BudgetPlan.id == plan.id).values(updated_at=func.now()))
    effective = min(today, plan.ends_on)
    current = spend_by_category(session, plan.starts_on, effective, plan.currency, tz).get(category_id, 0)
    delta = total_cents - current
    if delta == 0:
        return None
    when = datetime.combine(effective, time(12), zone(tz)).astimezone(timezone.utc).replace(tzinfo=None)
    return apply.create(session, occurred_at=when, merchant=None, amount_cents=-delta,
                        currency=plan.currency, category_id=category_id, source="adjustment",
                        granularity="aggregate_adjustment",
                        note=f"Adjusted {plan.period_type} {plan.starts_on}–{plan.ends_on} total to {Decimal(total_cents) / 100} {plan.currency}."
                             + (f" {note}" if note else ""))
