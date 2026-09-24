from datetime import date, datetime, timedelta

import pytest

from backend.services.budget import mutations as m
from backend.services.budget.periods import elapsed_days, period_bounds, utc_bounds
from backend.services.budget.projections import item_status, project_spend
from backend.services.budget.summary import get_plan_summary, get_period_spend
from backend.services.errors import ConflictError, ValidationError, CategoryInUseError
from backend.services.categories import delete_category
from backend.services.ledger import apply


@pytest.mark.parametrize("kind,on,start,end", [
    ("week", "2026-01-01", "2025-12-29", "2026-01-04"),
    ("week", "2026-09-27", "2026-09-21", "2026-09-27"),
    ("month", "2024-02-12", "2024-02-01", "2024-02-29"),
    ("month", "2025-02-28", "2025-02-01", "2025-02-28"),
])
def test_periods(kind, on, start, end):
    assert period_bounds(kind, date.fromisoformat(on)) == (date.fromisoformat(start), date.fromisoformat(end))


def test_dst_and_tokyo_bounds():
    low, high = utc_bounds(date(2026, 3, 8), date(2026, 3, 8), "America/New_York")
    assert high-low == timedelta(hours=23)
    assert utc_bounds(date(2026, 1, 1), date(2026, 1, 1), "Asia/Tokyo")[0] == datetime(2025, 12, 31, 15)


@pytest.mark.parametrize("spent,limit,elapsed,status", [(101,100,30,"over"),(80,100,15,"warning"),
    (80,100,30,"watch"),(60,100,30,"watch"),(59,100,1,"safe"),(0,0,0,"safe"),(1,0,0,"over")])
def test_status(spent, limit, elapsed, status):
    assert item_status(spent, limit, elapsed, 30) == status
    assert item_status(80,100,15,30, warning_ratio=0.9) == "watch"


def test_projection_and_elapsed():
    assert project_spend(100, 0, 30) == 0
    assert project_spend(100, 30, 30) == 100
    assert project_spend(101, 2, 7) == 354
    assert elapsed_days(date(2026,1,1),date(2026,1,31),date(2025,12,31)) == (0,31)
    assert elapsed_days(date(2026,1,1),date(2026,1,31),date(2026,2,2)) == (31,0)


def plan(session):
    p = m.create_plan(session, period_type="month", starts_on=date(2026,1,1), currency="JPY", planned_income_cents=30000000)
    m.add_item(session, p.id, category_id="food", limit_cents=100000)
    m.add_item(session, p.id, category_id="other", limit_cents=10000)
    return p


def txn(session, amount=-120000, currency="JPY", when=datetime(2026,1,10), category_id="food", **kw):
    return apply.create(session, merchant="Receipt", occurred_at=when, amount_cents=amount, currency=currency,
                        category_id=category_id, source="photo", **kw)


def test_aggregation_income_currency_boundaries_and_zero(session):
    p = plan(session)
    txn(session)
    txn(session, amount=900000)
    txn(session, amount=-700000, category_id="income")
    txn(session, currency="USD")
    txn(session, when=datetime(2025,12,31,14,59,59))
    txn(session, when=datetime(2026,1,31,15))
    txn(session, type="transfer_out", system=True)
    summary = get_plan_summary(session, p.id, date(2026,1,31))
    assert summary["actual_spend_cents"] == 120000  # JPY 1,200 remains 120000 stored cents
    assert summary["remaining_budget_cents"] == -10000
    assert summary["items"][0]["status"] == "over"
    assert summary["items"][1]["spent_cents"] == 0
    assert summary["projected_spend_cents"] == 120000
    assert summary["projected_savings_cents"] == 29880000


def test_adjustments_up_down_noop_and_delete(session):
    p = plan(session)
    original = txn(session)
    down = m.set_category_spend_total(session, plan_id=p.id, category_id="food", total_cents=85000, as_of=date(2026,1,15))
    assert down.amount_cents == 35000 and down.merchant is None
    assert down.source == "adjustment" and down.granularity == "aggregate_adjustment"
    assert original.amount_cents == -120000
    assert get_plan_summary(session, p.id, date(2026,1,15))["actual_spend_cents"] == 85000
    assert m.set_category_spend_total(session, plan_id=p.id, category_id="food", total_cents=85000, as_of=date(2026,1,15)) is None
    up = m.set_category_spend_total(session, plan_id=p.id, category_id="food", total_cents=210000, as_of=date(2026,1,15))
    assert up.amount_cents == -125000
    apply.delete(session, up.id)
    assert get_period_spend(session, "food", p.starts_on, p.ends_on, "JPY") == 85000


def test_clone_coexists_does_not_copy_spending(session):
    p = plan(session)
    txn(session)
    clone = m.clone_plan(session, p.id, date(2026,2,1))
    assert clone.items[0].id != p.items[0].id
    assert clone.planned_income_cents == p.planned_income_cents
    assert get_plan_summary(session, clone.id, date(2026,2,28))["actual_spend_cents"] == 0
    week = m.create_plan(session, period_type="week", starts_on=date(2026,1,5), currency="JPY")
    assert get_plan_summary(session, week.id, date(2026,1,11))["actual_spend_cents"] == 120000
    assert get_plan_summary(session, week.id, date(2026,1,11))["unbudgeted"]
    with pytest.raises(ConflictError):
        m.clone_plan(session, p.id, date(2026,2,1))


def test_future_and_validation(session):
    p = m.create_plan(session, period_type="month", starts_on=date(2099,1,1), currency="JPY")
    txn(session, when=datetime(2099,1,10))
    assert get_plan_summary(session, p.id)["actual_spend_cents"] == 0
    with pytest.raises(ValidationError):
        m.set_category_spend_total(session, plan_id=p.id, category_id="food", total_cents=100)
    with pytest.raises(ValidationError):
        m.create_plan(session, period_type="week", starts_on=date(2026,1,1), currency="JPY")
    with pytest.raises(ValidationError):
        m.add_item(session, p.id, category_id="food", limit_cents=-1)
    with pytest.raises(ValidationError):
        m.quick_expense(session, amount_cents=0, category_id="food", currency="JPY", occurred_on=date(2026,1,1))


@pytest.mark.parametrize("category_id", ["income", "transfer"])
def test_budget_writes_reject_non_spending_categories(session, category_id):
    p = m.create_plan(session, period_type="month", starts_on=date(2026,1,1), currency="JPY")
    with pytest.raises(ValidationError):
        m.add_item(session, p.id, category_id=category_id, limit_cents=100)
    with pytest.raises(ValidationError):
        m.quick_expense(session, amount_cents=100, category_id=category_id, currency="JPY",
                        occurred_on=date(2026,1,1))
    with pytest.raises(ValidationError):
        m.set_category_spend_total(session, plan_id=p.id, category_id=category_id,
                                   total_cents=100, as_of=date(2026,1,1))


def test_budget_protects_category_and_delete_cascades(session):
    from backend.db.models import BudgetItem
    p = plan(session)
    ids = [i.id for i in p.items]
    with pytest.raises(CategoryInUseError):
        delete_category(session, "food")
    m.delete_plan(session, p.id)
    assert all(session.get(BudgetItem, id) is None for id in ids)
