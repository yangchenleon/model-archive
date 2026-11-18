"""Photo rules: what a phone photo turns into before it is stored.

Everything here is about the fact that the bytes come from a phone: sideways
EXIF orientation, HEIC-free JPEG conversion, multi-megabyte files, and the same
picture uploaded twice. The API layer only passes bytes through.
"""

from __future__ import annotations

import hashlib
import io
from uuid import UUID

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AssetPhoto
from app.services.errors import Invalid, NotFound
from app.storage import get_storage

MAX_BYTES = 20 * 1024 * 1024
ORIGINAL_EDGE = 1920
THUMB_EDGE = 400
QUALITY = 85


def _flatten(image: Image.Image) -> Image.Image:
    """Drop transparency onto white: a bagged kit photo is not a logo."""
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGB", image.size, (255, 255, 255))
        canvas.paste(image, mask=image.split()[-1])
        return canvas
    return image.convert("RGB")


def _encode(image: Image.Image, edge: int) -> tuple[bytes, int, int]:
    image = _flatten(image)
    if max(image.size) > edge:
        image.thumbnail((edge, edge), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buffer.getvalue(), image.width, image.height


def prepare(raw: bytes) -> tuple[bytes, bytes, int, int]:
    """Return (original jpeg, thumbnail jpeg, width, height) for a phone photo."""
    if not raw:
        raise Invalid("空文件")
    if len(raw) > MAX_BYTES:
        raise Invalid(f"图片不能超过 {MAX_BYTES // 1024 // 1024} MB")
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception:  # Pillow raises several unrelated types for bad input
        raise Invalid("无法识别的图片格式（支持 JPEG / PNG / WebP）")
    # exif_transpose before _flatten: sideways photos are the common case and the
    # orientation tag must be applied while the pixels are still untouched.
    image = ImageOps.exif_transpose(image)
    original, width, height = _encode(image, ORIGINAL_EDGE)
    thumb, _, _ = _encode(image, THUMB_EDGE)
    return original, thumb, width, height


def _keys(digest: str) -> tuple[str, str]:
    """Shard by the first two hex chars: one flat prefix gets slow on S3 UIs."""
    return f"photos/{digest[:2]}/{digest}.jpg", f"photos/{digest[:2]}/{digest}_t.jpg"


def add(session: Session, asset_id: UUID, raw: bytes) -> AssetPhoto:
    """Store a photo for one asset. Re-uploading the same picture is a no-op."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise NotFound("资产不存在")
    original, thumb, width, height = prepare(raw)
    digest = hashlib.sha256(original).hexdigest()
    object_key, thumb_key = _keys(digest)

    existing = session.scalar(
        select(AssetPhoto).where(
            AssetPhoto.asset_id == asset.id, AssetPhoto.object_key == object_key
        )
    )
    if existing is not None:
        return existing

    storage = get_storage()
    storage.put(object_key, original)
    storage.put(thumb_key, thumb)

    photo = AssetPhoto(
        asset_id=asset.id,
        object_key=object_key,
        thumb_key=thumb_key,
        width=width,
        height=height,
        bytes=len(original),
    )
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


def load(session: Session, photo_id: UUID) -> AssetPhoto:
    photo = session.get(AssetPhoto, photo_id)
    if photo is None:
        raise NotFound("照片不存在")
    return photo


def read(session: Session, photo_id: UUID, thumb: bool = False) -> bytes:
    photo = load(session, photo_id)
    return get_storage().get(photo.thumb_key if thumb else photo.object_key)


def remove(session: Session, photo_id: UUID) -> None:
    """Delete the row, and the objects only when nothing else points at them."""
    photo = load(session, photo_id)
    object_key, thumb_key = photo.object_key, photo.thumb_key
    session.delete(photo)
    session.flush()
    still_used = session.scalar(
        select(AssetPhoto.id).where(AssetPhoto.object_key == object_key).limit(1)
    )
    if still_used is None:
        storage = get_storage()
        storage.delete(object_key)
        storage.delete(thumb_key)
    session.commit()
