"""Review queue endpoints: the audit gate between mentions and products."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import ReviewItem
from app.schemas import (
    ProductRead,
    ReviewCreateRequest,
    ReviewItemRead,
    ReviewList,
    ReviewMapRequest,
    ReviewSkipRequest,
)
from app.services import review as service

router = APIRouter(tags=["review"])


@router.get("/products/{product_id}/review-items", response_model=list[ReviewItemRead])
def list_product_review_items(product_id: UUID, session: Session = Depends(get_session)) -> list[ReviewItem]:
    return list(session.scalars(
        select(ReviewItem)
        .where(ReviewItem.product_id == product_id)
        .order_by(ReviewItem.event_date.desc(), ReviewItem.created_at.desc())
    ))


@router.get("/review/stats")
def review_stats(session: Session = Depends(get_session)) -> dict[str, int]:
    return service.stats(session)


@router.get("/review/items", response_model=ReviewList)
def review_items(
    state: str = "pending",
    q: str | None = None,
    sort: str = "brand",
    limit: int = Query(default=30, le=200),
    offset: int = 0,
    session: Session = Depends(get_session),
) -> ReviewList:
    return service.page(session, state=state, q=q, sort=sort, limit=limit, offset=offset)


@router.post("/review/{item_id}/map", response_model=ReviewItemRead)
def map_item(item_id: UUID, payload: ReviewMapRequest, session: Session = Depends(get_session)) -> ReviewItem:
    """Link the mention to an existing product; the product itself is untouched."""
    return service.map_to_product(session, item_id, payload)


@router.post("/review/{item_id}/create", response_model=ProductRead)
def create_from_item(item_id: UUID, payload: ReviewCreateRequest, session: Session = Depends(get_session)):
    return service.create_product(session, item_id, payload)


@router.post("/review/{item_id}/skip", response_model=ReviewItemRead)
def skip_item(
    item_id: UUID, payload: ReviewSkipRequest | None = None, session: Session = Depends(get_session)
) -> ReviewItem:
    return service.skip(session, item_id, payload)


@router.post("/review/{item_id}/reset", response_model=ReviewItemRead)
def reset_item(item_id: UUID, session: Session = Depends(get_session)) -> ReviewItem:
    return service.reset(session, item_id)
