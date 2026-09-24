from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.routes.transactions import _to_out as _txn_to_out
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.transfer import TransferCreate, TransferOut
from backend.services.ledger import transfers as transfer_svc

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.post("", response_model=Data[TransferOut], status_code=status.HTTP_201_CREATED)
def create_(body: TransferCreate, session: Session = Depends(get_session)) -> Data[TransferOut]:
    pair = transfer_svc.create_transfer(
        session,
        from_account_id=body.from_account_id,
        to_account_id=body.to_account_id,
        amount_cents=body.amount_cents,
        occurred_at=body.occurred_at,
        note=body.note,
    )
    session.commit()
    return Data(
        data=TransferOut(
            out_transaction=_txn_to_out(pair.out_transaction),
            in_transaction=_txn_to_out(pair.in_transaction),
            transfer_group_id=pair.transfer_group_id,
        )
    )


@router.delete("/{transfer_group_id}", response_model=Data[OkOut])
def delete_(transfer_group_id: str, session: Session = Depends(get_session)) -> Data[OkOut]:
    transfer_svc.delete_transfer(session, transfer_group_id)
    session.commit()
    return Data(data=OkOut())
