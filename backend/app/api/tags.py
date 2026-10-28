"""Sticker endpoints.

Declared before ``/assets/{asset_id}/...`` shapes so the literal ``bulk``
segment is not swallowed by the UUID path parameter.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AssetTag
from app.schemas import BulkTagCreate, BulkTagPrint, TagCreate, TagQueueItem, TagRead, TagUpdate
from app.services import tags as service

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[TagQueueItem])
def list_tags(
    status: str = "open",
    limit: int = Query(default=500, le=2000),
    session: Session = Depends(get_session),
) -> list[TagQueueItem]:
    """``open`` is the print queue; ``printed`` is where reprints are picked up."""
    return service.queue(session, status, limit)


@router.post("/assets/bulk/tags", response_model=list[TagRead], status_code=status.HTTP_201_CREATED)
def bulk_queue_tags(payload: BulkTagCreate, session: Session = Depends(get_session)) -> list[AssetTag]:
    """Back to the print queue: issue a sticker if missing, otherwise un-print it."""
    return service.requeue(session, payload)


@router.post("/assets/{asset_id}/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def add_tag(asset_id: UUID, payload: TagCreate, session: Session = Depends(get_session)) -> AssetTag:
    """Add one more bag; the next free seq picks the code suffix."""
    return service.issue(session, asset_id, payload.title)


@router.patch("/tags/{tag_id}", response_model=TagRead)
def rename_tag(tag_id: UUID, payload: TagUpdate, session: Session = Depends(get_session)) -> AssetTag:
    """Renaming keeps the code, so no sticker is wasted."""
    return service.rename(session, tag_id, payload.title)


@router.post("/tags/bulk/printed")
def bulk_print_tags(payload: BulkTagPrint, session: Session = Depends(get_session)) -> dict[str, int]:
    """Called by the print page; printing is what marks a sticker as applied."""
    return service.mark_many_printed(session, payload.tag_ids)


@router.post("/tags/{tag_id}/printed", response_model=TagRead)
def print_tag(tag_id: UUID, session: Session = Depends(get_session)) -> AssetTag:
    return service.mark_printed(session, tag_id)

