from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.deps import get_session
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from backend.db.models import Category
from backend.services.categories import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _to_out(c: Category) -> CategoryOut:
    return CategoryOut(
        id=c.id,
        label=c.label,
        color_bg=c.color_bg,
        color_dot=c.color_dot,
        keywords=list(c.keywords),
        auto_assign=c.auto_assign,
        sort_order=c.sort_order,
        created_at=c.created_at,
    )


@router.get("", response_model=Data[list[CategoryOut]])
def list_(session: Session = Depends(get_session)) -> Data[list[CategoryOut]]:
    return Data(data=[_to_out(c) for c in list_categories(session)])


@router.get("/{category_id}", response_model=Data[CategoryOut])
def get_(category_id: str, session: Session = Depends(get_session)) -> Data[CategoryOut]:
    return Data(data=_to_out(get_category(session, category_id)))


@router.post("", response_model=Data[CategoryOut], status_code=status.HTTP_201_CREATED)
def create_(
    body: CategoryCreate, session: Session = Depends(get_session)
) -> Data[CategoryOut]:
    cat = create_category(session, **body.model_dump(by_alias=False, exclude_unset=True))
    session.commit()
    return Data(data=_to_out(cat))


@router.patch("/{category_id}", response_model=Data[CategoryOut])
def update_(
    category_id: str,
    body: CategoryUpdate,
    session: Session = Depends(get_session),
) -> Data[CategoryOut]:
    cat = update_category(
        session,
        category_id,
        **body.model_dump(by_alias=False, exclude_unset=True),
    )
    session.commit()
    return Data(data=_to_out(cat))


@router.delete("/{category_id}", response_model=Data[OkOut])
def delete_(
    category_id: str, session: Session = Depends(get_session)
) -> Data[OkOut]:
    delete_category(session, category_id)
    session.commit()
    return Data(data=OkOut())
