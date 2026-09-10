"""Image upload API — stores files under uploads/ and returns a public URL."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

MAX_BYTES = 5 * 1024 * 1024  # 5 MB

UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "uploads"


class ImageUploadRead(BaseModel):
    url: str
    filename: str
    content_type: str
    size: int


@router.post("/images", response_model=ImageUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, GIF, WebP, or SVG images are allowed.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be 5 MB or smaller.",
        )

    ext = ALLOWED_CONTENT_TYPES[content_type]
    org_dir = UPLOAD_ROOT / current_user.organization_id
    org_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    dest = org_dir / filename
    dest.write_bytes(data)

    return ImageUploadRead(
        url=f"/uploads/{current_user.organization_id}/{filename}",
        filename=filename,
        content_type=content_type,
        size=len(data),
    )
