from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.merchant import MerchantAliasCreate, MerchantAliasOut
from backend.db.models import MerchantAlias
from backend.services import merchants as merchant_svc

router = APIRouter(prefix="/api/merchant-aliases", tags=["merchants"])


def _to_out(a: MerchantAlias) -> MerchantAliasOut:
    return MerchantAliasOut(
        id=a.id,
        raw_pattern=a.raw_pattern,
        match_type=a.match_type,
        merchant_id=a.merchant_id,
        applied_count=a.applied_count,
    )


@router.get("", response_model=Data[list[MerchantAliasOut]])
def list_(session: Session = Depends(get_session)) -> Data[list[MerchantAliasOut]]:
    return Data(data=[_to_out(a) for a in merchant_svc.list_aliases(session)])


@router.post("", response_model=Data[MerchantAliasOut], status_code=status.HTTP_201_CREATED)
def create_(
    body: MerchantAliasCreate, session: Session = Depends(get_session)
) -> Data[MerchantAliasOut]:
    alias = merchant_svc.create_alias(
        session,
        raw_pattern=body.raw_pattern,
        match_type=body.match_type,
        merchant_id=body.merchant_id,
    )
    session.commit()
    return Data(data=_to_out(alias))


@router.delete("/{alias_id}", response_model=Data[OkOut])
def delete_(alias_id: str, session: Session = Depends(get_session)) -> Data[OkOut]:
    merchant_svc.delete_alias(session, alias_id)
    session.commit()
    return Data(data=OkOut())
