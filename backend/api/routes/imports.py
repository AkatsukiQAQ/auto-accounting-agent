from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.api.config import AppConfig
from backend.api.deps import (
    get_config,
    get_llm,
    get_pipeline,
    get_pipeline_config,
    get_session,
)
from backend.api.schemas.base import Data
from backend.api.schemas.import_ import ImportPhotoData
from backend.api.schemas.transaction import RawIn, TransactionCreate
from backend.core.schemas import ClassificationResult, ParsedOcrResult, ParsedReceipt, ReceiptClassification
from backend.services.errors import UnsupportedImageError
from backend.services.pipeline import (
    ImportPipeline,
    PipelineConfig,
    PipelineLLM,
    StageContext,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/import", tags=["import"])

_SUFFIX_FROM_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

_UTC = timezone.utc


def _validate_image(upload: UploadFile) -> None:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise UnsupportedImageError(
            f"expected image upload, got content-type {upload.content_type!r}",
            meta={"contentType": upload.content_type},
        )
    header = upload.file.read(12)
    upload.file.seek(0)
    is_jpeg = header.startswith(b"\xff\xd8\xff")
    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")
    is_gif = header[:4] == b"GIF8"
    is_webp = header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    if not (is_jpeg or is_png or is_gif or is_webp):
        raise UnsupportedImageError(
            "file magic bytes don't match any supported image format (JPEG/PNG/GIF/WebP)"
        )


def _save_upload(upload: UploadFile, storage_dir: Path) -> tuple[Path, str]:
    """Save upload to {storage}/{YYYY}/{MM}/{uuid}.{ext}; return (absolute_path, relative_path)."""
    now = datetime.now(_UTC)
    rel_dir = f"{now.year:04d}/{now.month:02d}"
    target_dir = storage_dir / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    ext = _SUFFIX_FROM_MIME.get(upload.content_type or "", ".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"
    target = target_dir / filename
    with target.open("wb") as dest:
        shutil.copyfileobj(upload.file, dest)
    return target, f"{rel_dir}/{filename}"


def _parse_occurred_at(parsed: ParsedReceipt) -> datetime:
    if parsed.date:
        try:
            if parsed.time:
                return datetime.fromisoformat(f"{parsed.date}T{parsed.time}").replace(tzinfo=_UTC)
            return datetime.fromisoformat(parsed.date).replace(tzinfo=_UTC)
        except ValueError:
            pass
    return datetime.now(_UTC)


def _overall_confidence(
    parsed: ParsedReceipt, classified: ReceiptClassification | None
) -> float:
    """0.5 * parse_c + 0.5 * classify_c per design doc §Import."""
    if parsed.currency and parsed.amount is not None and parsed.date:
        parse_c = 1.0
    elif parsed.currency and parsed.amount is not None:
        parse_c = 0.7
    else:
        parse_c = 0.3

    if classified is None:
        classify_c = 0.0
    elif classified.matched and classified.keyword:
        classify_c = 1.0
    elif classified.matched:
        classify_c = 0.75
    else:
        classify_c = 0.4

    return 0.5 * parse_c + 0.5 * classify_c


def _build_preview(
    parsed: ParsedReceipt,
    classified: ReceiptClassification | None,
    public_image_url: str,
    raw_text: str,
    llm_model: str,
) -> TransactionCreate:
    amount_cents = (
        -round((parsed.amount or 0) * 100) if parsed.amount is not None else 0
    )
    category_id = "other"
    if classified is not None and classified.matched:
        category_id = classified.category
    return TransactionCreate(
        occurred_at=_parse_occurred_at(parsed),
        merchant=parsed.merchant or "Unknown",
        amount_cents=amount_cents,
        currency=parsed.currency or "USD",
        category_id=category_id,
        source="photo",
        confidence=_overall_confidence(parsed, classified),
        raw=RawIn(
            image_url=public_image_url,
            ocr_text=raw_text,
            ocr_engine=llm_model,
            llm_model=llm_model,
        ),
    )


def _placeholder_response(public_image_url: str, llm_model: str) -> ImportPhotoData:
    """Empty-OCR fallback: return one placeholder draft so the user can fill in manually."""
    placeholder = TransactionCreate(
        occurred_at=datetime.now(_UTC),
        merchant="Unknown",
        amount_cents=0,
        currency="USD",
        category_id="other",
        source="photo",
        confidence=0.0,
        raw=RawIn(
            image_url=public_image_url,
            ocr_text="",
            ocr_engine=llm_model,
            llm_model=llm_model,
        ),
    )
    return ImportPhotoData(
        preview_transactions=[placeholder],
        confidences=[0.0],
        ocr_text="",
        ocr_engine=llm_model,
        llm_model=llm_model,
    )


@router.post("/photo", response_model=Data[ImportPhotoData])
def post_photo(
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    llm: PipelineLLM = Depends(get_llm),
    pipeline: ImportPipeline = Depends(get_pipeline),
    pipeline_config: PipelineConfig = Depends(get_pipeline_config),
    config: AppConfig = Depends(get_config),
) -> Data[ImportPhotoData]:
    _validate_image(image)
    saved_path, rel_path = _save_upload(image, config.image_storage_dir)
    public_url = f"{config.image_public_base_url.rstrip('/')}/{rel_path}"

    result = pipeline.run(
        StageContext(llm=llm, session=session, config=pipeline_config),
        str(saved_path),
    )

    parsed_list: ParsedOcrResult = result.parsed
    classified_list: ClassificationResult = result.classified

    if not parsed_list.parsed_ocr_results:
        logger.info("OCR returned no receipts; returning placeholder draft")
        return Data(data=_placeholder_response(public_url, result.llm_model))

    classified_by_idx = {
        c.idx: c for c in classified_list.classification_results
    }

    previews: list[TransactionCreate] = []
    confidences: list[float] = []
    ocr_chunks: list[str] = []
    for i, parsed in enumerate(parsed_list.parsed_ocr_results):
        classified = classified_by_idx.get(i)
        previews.append(
            _build_preview(parsed, classified, public_url, parsed.raw_text, result.llm_model)
        )
        confidences.append(_overall_confidence(parsed, classified))
        if parsed.raw_text:
            ocr_chunks.append(parsed.raw_text)

    if len(previews) > 1:
        logger.info("multi-receipt image had %d receipts; returning all", len(previews))

    return Data(
        data=ImportPhotoData(
            preview_transactions=previews,
            confidences=confidences,
            ocr_text="\n\n".join(ocr_chunks),
            ocr_engine=result.llm_model,
            llm_model=result.llm_model,
        )
    )
