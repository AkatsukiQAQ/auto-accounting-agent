from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.budget import (
    CloneInput, ItemCreate, ItemOut, ItemUpdate, PeriodType, PlanCreate, PlanOut,
    PlanUpdate, QuickInput, SetTotalInput, SummaryOut,
)
from backend.api.schemas.transaction import TransactionOut
from backend.api.routes.transactions import _to_out
from backend.services.budget import mutations as svc
from backend.services.budget.summary import get_active_plan, get_plan_summary, profile_context

router = APIRouter(prefix="/api", tags=["budgets"])


@router.get("/budget-plans", response_model=Data[list[PlanOut]])
def list_(session: Session = Depends(get_session), period_type: PeriodType | None = Query(None, alias="periodType"),
          start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
          currency: str | None = None):
    return Data(data=[PlanOut.model_validate(p) for p in svc.list_plans(session, period_type=period_type,
                     start=start, end=end, currency=currency)])


@router.post("/budget-plans", response_model=Data[PlanOut], status_code=201)
def create(body: PlanCreate, session: Session = Depends(get_session)):
    plan = svc.create_plan(session, **body.model_dump())
    session.commit()
    return Data(data=PlanOut.model_validate(plan))


@router.get("/budget-plans/{plan_id}", response_model=Data[PlanOut])
def get(plan_id: str, session: Session = Depends(get_session)):
    return Data(data=PlanOut.model_validate(svc.get_plan(session, plan_id)))


@router.patch("/budget-plans/{plan_id}", response_model=Data[PlanOut])
def update(plan_id: str, body: PlanUpdate, session: Session = Depends(get_session)):
    plan = svc.update_plan(session, plan_id, **body.model_dump(exclude_unset=True))
    session.commit()
    return Data(data=PlanOut.model_validate(plan))


@router.delete("/budget-plans/{plan_id}", response_model=Data[OkOut])
def delete(plan_id: str, session: Session = Depends(get_session)):
    svc.delete_plan(session, plan_id)
    session.commit()
    return Data(data=OkOut())


@router.post("/budget-plans/{plan_id}/clone", response_model=Data[PlanOut], status_code=201)
def clone(plan_id: str, body: CloneInput, session: Session = Depends(get_session)):
    plan = svc.clone_plan(session, plan_id, **body.model_dump())
    session.commit()
    return Data(data=PlanOut.model_validate(plan))


@router.post("/budget-plans/{plan_id}/items", response_model=Data[ItemOut], status_code=201)
def add_item(plan_id: str, body: ItemCreate, session: Session = Depends(get_session)):
    item = svc.add_item(session, plan_id, **body.model_dump())
    session.commit()
    return Data(data=ItemOut.model_validate(item))


@router.patch("/budget-items/{item_id}", response_model=Data[ItemOut])
def update_item(item_id: str, body: ItemUpdate, session: Session = Depends(get_session)):
    item = svc.update_item(session, item_id, **body.model_dump(exclude_unset=True))
    session.commit()
    return Data(data=ItemOut.model_validate(item))


@router.delete("/budget-items/{item_id}", response_model=Data[OkOut])
def delete_item(item_id: str, session: Session = Depends(get_session)):
    svc.delete_item(session, item_id)
    session.commit()
    return Data(data=OkOut())


@router.get("/budget-plans/{plan_id}/summary", response_model=Data[SummaryOut])
def summary(plan_id: str, session: Session = Depends(get_session), as_of: date | None = Query(None, alias="asOf")):
    return Data(data=SummaryOut.model_validate(get_plan_summary(session, plan_id, as_of)))


@router.get("/budget-summary/current", response_model=Data[SummaryOut | None])
def current(session: Session = Depends(get_session), period_type: PeriodType = Query("month", alias="periodType"),
            on_date: date | None = Query(None, alias="onDate"), currency: str | None = None):
    _, default_currency, today = profile_context(session)
    plan = get_active_plan(session, period_type, on_date or today, currency or default_currency)
    return Data(data=SummaryOut.model_validate(get_plan_summary(session, plan.id)) if plan else None)


@router.post("/transactions/quick", response_model=Data[TransactionOut], status_code=201)
def quick(body: QuickInput, session: Session = Depends(get_session)):
    row = svc.quick_expense(session, **body.model_dump())
    session.commit()
    return Data(data=_to_out(row))


@router.post("/budget-spend/set-total", response_model=Data[TransactionOut | None])
def set_total(body: SetTotalInput, session: Session = Depends(get_session)):
    row = svc.set_category_spend_total(session, **body.model_dump())
    session.commit()
    return Data(data=_to_out(row) if row else None)
