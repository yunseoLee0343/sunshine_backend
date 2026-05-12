"""Uploads API — T-003B: plant image upload and opaque image_ref generation."""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.uploads import PlantImageUploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

_ALLOWED: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

_SUBDIR = "plant-images"


@router.post("/plant-image", response_model=PlantImageUploadResponse, status_code=201)
async def upload_plant_image(file: UploadFile = File(...)) -> PlantImageUploadResponse:
    content_type = file.content_type or ""
    ext = _ALLOWED.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported media type '{content_type}'. "
                f"Accepted: {', '.join(_ALLOWED)}"
            ),
        )

    data = await file.read()
    size = len(data)

    if size > settings.UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {size} bytes. "
                f"Maximum allowed: {settings.UPLOAD_MAX_BYTES} bytes."
            ),
        )

    upload_dir = Path(settings.UPLOAD_DIR) / _SUBDIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext}"
    (upload_dir / filename).write_bytes(data)

    return PlantImageUploadResponse(
        image_ref=f"uploads/{_SUBDIR}/{filename}",
        content_type=content_type,
        size_bytes=size,
    )
