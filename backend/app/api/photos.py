"""Photo endpoints: upload for one asset, then read bytes back by photo id.

Reads are keyed by photo id (not by object key) so the bucket layout stays
internal, and the response is immutable-cacheable: the id never changes content.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AssetPhoto
from app.schemas import AssetPhotoRead
from app.services import photos as service

router = APIRouter(tags=["photos"])

# The API proxies the bytes instead of handing out presigned URLs: exactly one
# port is exposed to the phone, and the bucket never needs to be public.
CACHE = "public, max-age=604800, immutable"


@router.post(
    "/assets/{asset_id}/photos",
    response_model=AssetPhotoRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    asset_id: UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> AssetPhoto:
    # Read one byte past the limit so an oversized upload is rejected without
    # buffering the whole file in memory.
    raw = file.file.read(service.MAX_BYTES + 1)
    return service.add(session, asset_id, raw)


@router.get("/photos/{photo_id}")
def read_photo(
    photo_id: UUID,
    size: str = Query(default="full", pattern="^(full|thumb)$"),
    session: Session = Depends(get_session),
) -> Response:
    body = service.read(session, photo_id, thumb=size == "thumb")
    return Response(content=body, media_type="image/jpeg", headers={"Cache-Control": CACHE})


@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(photo_id: UUID, session: Session = Depends(get_session)) -> Response:
    service.remove(session, photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
