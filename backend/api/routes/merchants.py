from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data
from backend.api.schemas.merchant import MerchantCreate, MerchantOut, MerchantUpdate
from backend.db.models import Merchant
from backend.services import merchants as merchant_svc

router = APIRouter(prefix="/api/merchants", tags=["merchants"])


def _to_out(m: Merchant) -> MerchantOut:
    return MerchantOut(
        id=m.id,
        canonical_name=m.canonical_name,
        aliases=[str(a) for a in m.aliases],
        default_category_id=m.default_category_id,
        logo_url=m.logo_url,
        source=m.source,
    )


@router.get("", response_model=Data[list[MerchantOut]])
def list_(
    session: Session = Depends(get_session),
    q: Optional[str] = Query(None, description="Substring match on canonical name or aliases"),
) -> Data[list[MerchantOut]]:
    return Data(data=[_to_out(m) for m in merchant_svc.list_merchants(session, q=q)])


@router.post("", response_model=Data[MerchantOut], status_code=status.HTTP_201_CREATED)
def create_(body: MerchantCreate, session: Session = Depends(get_session)) -> Data[MerchantOut]:
    merchant = merchant_svc.create_merchant(session, **body.model_dump(by_alias=False))
    session.commit()
    return Data(data=_to_out(merchant))


@router.patch("/{merchant_id}", response_model=Data[MerchantOut])
def update_(
    merchant_id: str, body: MerchantUpdate, session: Session = Depends(get_session)
) -> Data[MerchantOut]:
    merchant = merchant_svc.update_merchant(
        session, merchant_id, **body.model_dump(by_alias=False, exclude_unset=True)
    )
    session.commit()
    return Data(data=_to_out(merchant))
