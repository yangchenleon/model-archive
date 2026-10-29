"""Review queue rules: map a mention to a product, create one, or skip it."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Product, ReviewItem
from app.schemas import ProductCreate, ReviewCreateRequest, ReviewList, ReviewMapRequest, ReviewSkipRequest
from app.services import products as products_service
from app.services.errors import Invalid, NotFound

SKIP_REASONS = {"later", "ad", "duplicate", "invalid"}


def _require_pending(session: Session, item_id: UUID, missing: str = "待审核条目不存在或已处理") -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None or item.state != "pending":
        raise NotFound(missing)
    return item


def stats(session: Session) -> dict[str, int]:
    rows = session.execute(select(ReviewItem.state, func.count()).group_by(ReviewItem.state)).all()
    counts = {state: count for state, count in rows}
    later = session.scalar(
        select(func.count()).select_from(ReviewItem).where(
            ReviewItem.state == "skipped", ReviewItem.skip_reason == "later"
        )
    ) or 0
    return {
        "pending": counts.get("pending", 0),
        "mapped": counts.get("mapped", 0),
        "created": counts.get("created", 0),
        "skipped": counts.get("skipped", 0),
        "later": later,
        "total": sum(counts.values()),
    }


def page(session: Session, *, state: str, q: str | None, sort: str, limit: int, offset: int) -> ReviewList:
    base = select(ReviewItem)
    if state != "all":
        base = base.where(ReviewItem.state == state)
    if q:
        term = f"%{q.strip()}%"
        base = base.where(or_(
            ReviewItem.product.ilike(term),
            ReviewItem.brand.ilike(term),
            ReviewItem.evidence.ilike(term),
        ))
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    if sort == "date":
        order = (ReviewItem.event_date, ReviewItem.start_seconds, ReviewItem.brand)
    elif sort == "product":
        order = (ReviewItem.product.nulls_last(), ReviewItem.brand.nulls_last(), ReviewItem.event_date)
    else:
        order = (
            ReviewItem.brand.nulls_last(),
            ReviewItem.product.nulls_last(),
            ReviewItem.event_date,
            ReviewItem.start_seconds,
        )
    statement = base.order_by(*order).offset(offset).limit(limit)
    return ReviewList(total=total, items=list(session.scalars(statement)))


def map_to_product(session: Session, item_id: UUID, payload: ReviewMapRequest) -> ReviewItem:
    """Only links the mention to a product; the product itself is untouched."""
    item = _require_pending(session, item_id)
    product = session.get(Product, payload.product_id)
    if product is None:
        raise NotFound("目标产品不存在")
    item.product_id = product.id
    item.manufacturer_id = product.manufacturer_id
    item.product_line_id = product.product_line_id
    item.state = "mapped"
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(item)
    return item


def create_product(session: Session, item_id: UUID, payload: ReviewCreateRequest) -> Product:
    item = _require_pending(session, item_id)
    kit_name = payload.kit_name.strip()
    if not kit_name:
        raise Invalid("产品名称不能为空")

    product = products_service.create(session, ProductCreate(
        manufacturer_id=payload.manufacturer_id,
        product_line_id=payload.product_line_id,
        product_code=(payload.product_code.strip() if payload.product_code and payload.product_code.strip() else None),
        kit_name=kit_name,
        release_channel=payload.release_channel,
        detail=payload.detail or item.detail,
        source=f"https://www.bilibili.com/video/{item.video_id}" if item.video_id else "手动录入",
        price=(payload.price_text.strip() if payload.price_text and payload.price_text.strip() else None),
    ))
    item.product_id = product.id
    item.manufacturer_id = product.manufacturer_id
    item.product_line_id = product.product_line_id
    item.state = "created"
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    return product


def skip(session: Session, item_id: UUID, payload: ReviewSkipRequest | None) -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise NotFound("条目不存在")
    reason = payload.reason if payload else "later"
    if reason not in SKIP_REASONS:
        raise Invalid(f"reason 必须是 {sorted(SKIP_REASONS)} 之一")
    item.state = "skipped"
    item.skip_reason = reason
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(item)
    return item


def reset(session: Session, item_id: UUID) -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise NotFound("条目不存在")
    item.state = "pending"
    item.skip_reason = None
    item.product_id = None
    item.manufacturer_id = None
    item.product_line_id = None
    item.reviewed_at = None
    session.commit()
    session.refresh(item)
    return item
