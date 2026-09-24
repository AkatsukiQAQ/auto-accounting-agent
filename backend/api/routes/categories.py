from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from backend.api.config import AppConfig
from backend.api.deps import get_config, get_session
from backend.api.schemas.base import Data, OkOut
from backend.api.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from backend.db.models import Category
from backend.services.categories import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    set_category_icon_image,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _to_out(c: Category) -> CategoryOut:
    return CategoryOut(
        id=c.id,
        label=c.label,
        color_bg=c.color_bg,
        color_dot=c.color_dot,
        icon=c.icon,
        icon_image_url=c.icon_image_url,
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


@router.post("/{category_id}/icon-image", response_model=Data[CategoryOut])
def upload_icon_image(
    category_id: str,
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    config: AppConfig = Depends(get_config),
) -> Data[CategoryOut]:
    """Store a small category icon beneath the existing local media mount."""
    suffixes = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if image.content_type not in suffixes:
        from backend.services.errors import UnsupportedImageError
        raise UnsupportedImageError("Category icon must be a PNG, JPEG, or WebP image")
    image.file.seek(0, 2)
    size = image.file.tell()
    image.file.seek(0)
    if size > 512 * 1024:
        from backend.services.errors import UnsupportedImageError
        raise UnsupportedImageError("Category icon must be 512 KB or smaller")
    header = image.file.read(12)
    image.file.seek(0)
    valid = (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")
             or (header[:4] == b"RIFF" and header[8:12] == b"WEBP"))
    if not valid:
        from backend.services.errors import UnsupportedImageError
        raise UnsupportedImageError("Category icon file does not match its image format")
    directory = config.image_storage_dir / "category-icons"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffixes[image.content_type]}"
    with (directory / filename).open("wb") as destination:
        shutil.copyfileobj(image.file, destination)
    url = f"{config.image_public_base_url.rstrip('/')}/category-icons/{filename}"
    cat = set_category_icon_image(session, category_id, url)
    session.commit()
    return Data(data=_to_out(cat))


@router.delete("/{category_id}", response_model=Data[OkOut])
def delete_(
    category_id: str, session: Session = Depends(get_session)
) -> Data[OkOut]:
    delete_category(session, category_id)
    session.commit()
    return Data(data=OkOut())
