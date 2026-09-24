from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.routes.transactions import _to_out as _txn_to_out
from backend.api.schemas.account import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    ReconcileIn,
    ReconcileOut,
)
from backend.api.schemas.base import Data, OkOut
from backend.db.models import Account
from backend.services.ledger import accounts as account_svc

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _to_out(a: Account) -> AccountOut:
    return AccountOut(
        id=a.id,
        name=a.name,
        kind=a.kind,
        currency=a.currency,
        balance_cents=a.balance_cents,
        opening_balance_cents=a.opening_balance_cents,
        institution=a.institution,
        color=a.color,
        archived=a.archived,
        sort_order=a.sort_order,
        created_at=a.created_at,
    )


@router.get("", response_model=Data[list[AccountOut]])
def list_(session: Session = Depends(get_session)) -> Data[list[AccountOut]]:
    return Data(data=[_to_out(a) for a in account_svc.list_accounts(session)])


@router.get("/{account_id}", response_model=Data[AccountOut])
def get_(account_id: str, session: Session = Depends(get_session)) -> Data[AccountOut]:
    return Data(data=_to_out(account_svc.get_account(session, account_id)))


@router.post("", response_model=Data[AccountOut], status_code=status.HTTP_201_CREATED)
def create_(body: AccountCreate, session: Session = Depends(get_session)) -> Data[AccountOut]:
    account = account_svc.create_account(
        session, **body.model_dump(by_alias=False)
    )
    session.commit()
    return Data(data=_to_out(account))


@router.patch("/{account_id}", response_model=Data[AccountOut])
def update_(
    account_id: str, body: AccountUpdate, session: Session = Depends(get_session)
) -> Data[AccountOut]:
    account = account_svc.update_account(
        session, account_id, **body.model_dump(by_alias=False, exclude_unset=True)
    )
    session.commit()
    return Data(data=_to_out(account))


@router.delete("/{account_id}", response_model=Data[OkOut])
def delete_(account_id: str, session: Session = Depends(get_session)) -> Data[OkOut]:
    account_svc.delete_account(session, account_id)
    session.commit()
    return Data(data=OkOut())


@router.post("/{account_id}/reconcile", response_model=Data[ReconcileOut])
def reconcile_(
    account_id: str, body: ReconcileIn, session: Session = Depends(get_session)
) -> Data[ReconcileOut]:
    account, adjustment = account_svc.reconcile(
        session, account_id, actual_balance_cents=body.actual_balance_cents
    )
    session.commit()
    return Data(
        data=ReconcileOut(
            account=_to_out(account),
            adjustment=_txn_to_out(adjustment) if adjustment is not None else None,
        )
    )


@router.post("/{account_id}/recompute-balance", response_model=Data[AccountOut])
def recompute_(account_id: str, session: Session = Depends(get_session)) -> Data[AccountOut]:
    """Ops endpoint (not in PHASE_2.md): full rebuild of the materialized
    balance — the escape hatch if a bug ever lets it drift."""
    account = account_svc.recompute_balance(session, account_id)
    session.commit()
    return Data(data=_to_out(account))
