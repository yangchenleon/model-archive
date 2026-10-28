from __future__ import annotations

import io
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
import segno
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Asset, AssetStateChange, AssetTag, Product, ReviewItem
from app.schemas import (
    AssetCreate,
    AssetRead,
    AssetStateChangeRead,
    AssetUpdate,
    BulkAssetCreate,
    BulkStateUpdate,
    BulkTagPrint,
    BulkTagCreate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ReviewCreateRequest,
    ReviewItemRead,
    ReviewList,
    ReviewMapRequest,
    ReviewSkipRequest,
    TagCreate,
    TagQueueItem,
    TagRead,
    TagUpdate,
)

app = FastAPI(title="Model Archive API", version="0.5.0")

SKIP_REASONS = {"later", "ad", "duplicate", "invalid"}
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "outputs/daily_reports"))
VIDEO_ID = re.compile(r"^[A-Za-z0-9]+$")
DATE = re.compile(r"^\d{8}$")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)) -> Product:
    kit_name = payload.kit_name.strip()
    if not kit_name:
        raise HTTPException(status_code=422, detail="产品名称不能为空")
    duplicate = find_duplicate(session, payload.manufacturer, kit_name)
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="已存在同名同厂商产品")
    product = Product(**{**payload.model_dump(), "kit_name": kit_name})
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@app.post("/api/v1/products/bulk", response_model=list[ProductRead], status_code=status.HTTP_201_CREATED)
def bulk_create_products(payload: list[ProductCreate], session: Session = Depends(get_session)) -> list[Product]:
    """Create many products atomically.

    CSV/JSON importers are expected to live outside the project: they parse their
    own format and call this endpoint (or the single-product one) with clean
    values. Any duplicate aborts the whole batch — no partial inserts.
    """
    if not payload:
        raise HTTPException(status_code=422, detail="至少提交一条产品")
    if len(payload) > 500:
        raise HTTPException(status_code=422, detail="单次最多 500 条")

    seen: set[tuple[str | None, str]] = set()
    products: list[Product] = []
    for index, item in enumerate(payload, start=1):
        kit_name = item.kit_name.strip()
        if not kit_name:
            raise HTTPException(status_code=422, detail=f"第 {index} 条产品名称为空")
        key = (item.manufacturer, kit_name)
        if key in seen:
            raise HTTPException(status_code=409, detail=f"第 {index} 条与本次提交内的产品重复：{kit_name}")
        if find_duplicate(session, item.manufacturer, kit_name) is not None:
            raise HTTPException(status_code=409, detail=f"第 {index} 条已存在同名同厂商产品：{kit_name}")
        seen.add(key)
        product = Product(**{**item.model_dump(), "kit_name": kit_name})
        session.add(product)
        products.append(product)

    session.commit()
    for product in products:
        session.refresh(product)
    return products


@app.get("/api/v1/products", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    limit: int = Query(default=100, le=2000),
    session: Session = Depends(get_session),
) -> list[Product]:
    statement = select(Product).order_by(
        Product.manufacturer.nulls_last(),
        Product.product_line.nulls_last(),
        Product.product_code.nulls_last(),
        Product.kit_name,
    ).limit(limit)
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(
            Product.kit_name.ilike(term),
            Product.manufacturer.ilike(term),
            Product.product_line.ilike(term),
            Product.product_code.ilike(term),
        ))
    return list(session.scalars(statement))


@app.get("/api/v1/products/{product_id}", response_model=ProductRead)
def get_product(product_id: UUID, session: Session = Depends(get_session)) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


@app.patch("/api/v1/products/{product_id}", response_model=ProductRead)
def update_product(product_id: UUID, payload: ProductUpdate, session: Session = Depends(get_session)) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    data = payload.model_dump(exclude_unset=True)
    if "kit_name" in data:
        name = (data["kit_name"] or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="产品名称不能为空")
        data["kit_name"] = name
    if "source" in data:
        source = (data["source"] or "").strip()
        if not source:
            raise HTTPException(status_code=422, detail="资料来源不能为空")
        data["source"] = source
    new_name = data.get("kit_name", product.kit_name)
    new_manufacturer = data.get("manufacturer", product.manufacturer)
    duplicate = find_duplicate(session, new_manufacturer, new_name, exclude_id=product.id)
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="已存在同名同厂商产品")
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(product, field, value)
    session.commit()
    session.refresh(product)
    return product


@app.delete("/api/v1/products/{product_id}")
def delete_product(product_id: UUID, session: Session = Depends(get_session)) -> dict[str, str | int]:
    """Delete a product and return linked review items to the queue.

    There are no timeline rows to cascade any more; the only cross-table effect
    is that audit rows pointing at the product must not be left mapped to
    nothing.
    """
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    linked = session.scalar(
        select(func.count()).select_from(ReviewItem).where(ReviewItem.product_id == product_id)
    ) or 0
    if linked:
        session.execute(
            update(ReviewItem)
            .where(ReviewItem.product_id == product_id)
            .values(state="pending", product_id=None, skip_reason=None, reviewed_at=None)
        )
    session.delete(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="该产品仍被资产引用，无法删除")
    return {"deleted": str(product_id), "review_items_reset": linked}


ASSET_STATES = {"pending", "keep", "displayed", "stored", "sold"}
TAG_TITLE_MAX = 24


def load_asset(session: Session, asset_id: UUID) -> Asset:
    asset = session.scalar(
        select(Asset)
        .where(Asset.id == asset_id)
        .options(selectinload(Asset.product), selectinload(Asset.tags))
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@app.post("/api/v1/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> Asset:
    """Create one owned kit. Buying the same kit twice creates two rows."""
    if payload.state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail=f"state 必须是 {sorted(ASSET_STATES)} 之一")
    product = session.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="产品不存在")
    asset = Asset(product_id=product.id, **payload.model_dump(exclude={"product_id"}))
    session.add(asset)
    session.flush()
    # The first state is a transition from nothing; keep the audit complete.
    session.add(AssetStateChange(asset_id=asset.id, from_state=None, to_state=asset.state))
    session.commit()
    session.refresh(asset)
    _ = asset.product, asset.tags
    return asset


@app.get("/api/v1/assets", response_model=list[AssetRead])
def list_assets(
    state: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
    session: Session = Depends(get_session),
) -> list[Asset]:
    statement = (
        select(Asset)
        .options(selectinload(Asset.product), selectinload(Asset.tags))
        .order_by(Asset.code.desc())
        .limit(limit)
    )
    if state and state != "all":
        statement = statement.where(Asset.state == state)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.join(Product).where(
            or_(Asset.code.ilike(term), Product.kit_name.ilike(term))
        )
    return list(session.scalars(statement))


@app.post("/api/v1/assets/bulk", response_model=list[AssetRead], status_code=status.HTTP_201_CREATED)
def bulk_create_assets(payload: BulkAssetCreate, session: Session = Depends(get_session)) -> list[Asset]:
    """Backlog entry: register N products at once, each with an initial state."""
    if payload.state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail=f"state 必须是 {sorted(ASSET_STATES)} 之一")
    if not payload.product_ids:
        raise HTTPException(status_code=422, detail="至少选择一个产品")
    if len(payload.product_ids) > 200:
        raise HTTPException(status_code=422, detail="单次最多 200 条")
    known = set(session.scalars(select(Product.id).where(Product.id.in_(payload.product_ids))))
    missing = [str(pid) for pid in payload.product_ids if pid not in known]
    if missing:
        raise HTTPException(status_code=404, detail=f"产品不存在：{missing[0]}")
    assets = [
        Asset(product_id=pid, state=payload.state, acquired_on=payload.acquired_on)
        for pid in payload.product_ids
    ]
    session.add_all(assets)
    session.flush()
    for asset in assets:
        session.add(AssetStateChange(asset_id=asset.id, from_state=None, to_state=asset.state))
    session.commit()
    for asset in assets:
        session.refresh(asset)
        _ = asset.product, asset.tags
    return assets


@app.post("/api/v1/assets/bulk/state")
def bulk_update_state(payload: BulkStateUpdate, session: Session = Depends(get_session)) -> dict[str, int]:
    """One transition for many assets. Selling also retires their stickers."""
    if payload.state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail=f"state 必须是 {sorted(ASSET_STATES)} 之一")
    assets = list(session.scalars(
        select(Asset).where(Asset.id.in_(payload.asset_ids)).options(selectinload(Asset.tags))
    ))
    found = {asset.id for asset in assets}
    missing = [str(aid) for aid in payload.asset_ids if aid not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"资产不存在：{missing[0]}")
    changed = 0
    for asset in assets:
        if asset.state == payload.state:
            continue
        session.add(
            AssetStateChange(
                asset_id=asset.id,
                from_state=asset.state,
                to_state=payload.state,
                note=payload.note,
            )
        )
        asset.state = payload.state
        changed += 1
    session.commit()
    return {"updated": len(assets), "changed": changed}


@app.post("/api/v1/assets/bulk/tags", response_model=list[TagRead], status_code=status.HTTP_201_CREATED)
def bulk_create_tags(payload: BulkTagCreate, session: Session = Depends(get_session)) -> list[AssetTag]:
    """Hand one sticker to every asset that has none yet.

    Regenerating is a *reprint* of the same bag, not a new bag, so assets that
    already carry a sticker are skipped and reported back to the caller.
    """
    title = (payload.title or "").strip() or "本体"
    if len(title) > TAG_TITLE_MAX:
        raise HTTPException(status_code=422, detail=f"袋名最多 {TAG_TITLE_MAX} 个字符")
    assets = list(session.scalars(
        select(Asset).where(Asset.id.in_(payload.asset_ids)).options(selectinload(Asset.tags))
    ))
    found = {asset.id for asset in assets}
    missing = [str(aid) for aid in payload.asset_ids if aid not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"资产不存在：{missing[0]}")
    created: list[AssetTag] = []
    for asset in assets:
        if asset.tags:
            continue
        tag = AssetTag(asset_id=asset.id, seq=1, code=asset.code, title=title)
        session.add(tag)
        created.append(tag)
    session.commit()
    for tag in created:
        session.refresh(tag)
    return created


@app.post("/api/v1/tags/bulk/printed")
def bulk_print_tags(payload: BulkTagPrint, session: Session = Depends(get_session)) -> dict[str, int]:
    """Called by the print page. Printing is the only observable event, and a
    reprint is the same sticker, so this simply moves ``printed_at`` forward."""
    now = datetime.now(timezone.utc)
    tags = list(session.scalars(select(AssetTag).where(AssetTag.id.in_(payload.tag_ids))))
    printed = 0
    for tag in tags:
        tag.printed_at = now
        printed += 1
    session.commit()
    return {"requested": len(payload.tag_ids), "printed": printed}


@app.get("/api/v1/tags", response_model=list[TagQueueItem])
def list_tags(
    status: str = "open",
    limit: int = Query(default=500, le=2000),
    session: Session = Depends(get_session),
) -> list[TagQueueItem]:
    """``open`` is the print queue; ``printed`` is what has already come out, so
    a damaged sticker can be found and printed again."""
    statement = (
        select(AssetTag, Asset, Product)
        .join(Asset, AssetTag.asset_id == Asset.id)
        .join(Product, Asset.product_id == Product.id)
        .order_by(AssetTag.code)
        .limit(limit)
    )
    if status == "open":
        statement = statement.where(AssetTag.printed_at.is_(None))
    elif status == "printed":
        statement = statement.where(AssetTag.printed_at.is_not(None))
    return [
        TagQueueItem(
            id=tag.id,
            code=tag.code,
            seq=tag.seq,
            title=tag.title,
            asset_id=asset.id,
            asset_code=asset.code,
            kit_name=product.kit_name,
            manufacturer=product.manufacturer,
            product_line=product.product_line,
            created_at=tag.created_at,
            printed_at=tag.printed_at,
        )
        for tag, asset, product in session.execute(statement).all()
    ]


@app.get("/api/v1/qr")
def qr(data: str, scale: int = Query(default=8, le=20)) -> Response:
    """Bare SVG so the print page can place a code without bundling a font."""
    symbol = segno.make(data, error="m")
    buffer = io.BytesIO()
    # Standalone SVG: an <img src> needs the xmlns declaration that segno's
    # inline output deliberately omits, otherwise the image silently fails.
    symbol.save(buffer, kind="svg", scale=scale, border=2)
    return Response(content=buffer.getvalue(), media_type="image/svg+xml")


@app.get("/api/v1/assets/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: UUID, session: Session = Depends(get_session)) -> Asset:
    return load_asset(session, asset_id)


@app.patch("/api/v1/assets/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: UUID, payload: AssetUpdate, session: Session = Depends(get_session)) -> Asset:
    """Field edits are silent; a state change also writes an audit row."""
    asset = load_asset(session, asset_id)
    data = payload.model_dump(exclude_unset=True)
    new_state = data.get("state")
    if new_state is not None and new_state not in ASSET_STATES:
        raise HTTPException(status_code=422, detail=f"state 必须是 {sorted(ASSET_STATES)} 之一")
    if new_state is not None and new_state != asset.state:
        session.add(AssetStateChange(asset_id=asset.id, from_state=asset.state, to_state=new_state))
        data.pop("state")
        asset.state = new_state
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(asset, field, value)
    session.commit()
    session.refresh(asset)
    _ = asset.product, asset.tags
    return asset


@app.get("/api/v1/assets/{asset_id}/state-changes", response_model=list[AssetStateChangeRead])
def list_state_changes(asset_id: UUID, session: Session = Depends(get_session)) -> list[AssetStateChange]:
    if session.get(Asset, asset_id) is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return list(session.scalars(
        select(AssetStateChange)
        .where(AssetStateChange.asset_id == asset_id)
        .order_by(AssetStateChange.changed_at, AssetStateChange.id)
    ))


@app.post("/api/v1/assets/{asset_id}/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def add_tag(asset_id: UUID, payload: TagCreate, session: Session = Depends(get_session)) -> AssetTag:
    """Add one more bag to an asset. The next free seq picks the code suffix."""
    title = (payload.title or "").strip() or "本体"
    if len(title) > TAG_TITLE_MAX:
        raise HTTPException(status_code=422, detail=f"袋名最多 {TAG_TITLE_MAX} 个字符")
    asset = load_asset(session, asset_id)
    last_seq = session.scalar(select(func.max(AssetTag.seq)).where(AssetTag.asset_id == asset.id)) or 0
    seq = last_seq + 1
    tag = AssetTag(
        asset_id=asset.id,
        seq=seq,
        code=asset.code if seq == 1 else f"{asset.code}-{seq}",
        title=title,
    )
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@app.patch("/api/v1/tags/{tag_id}", response_model=TagRead)
def rename_tag(tag_id: UUID, payload: TagUpdate, session: Session = Depends(get_session)) -> AssetTag:
    """Renaming a bag is cheap; the code stays the same, so no sticker is wasted."""
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="袋名不能为空")
    if len(title) > TAG_TITLE_MAX:
        raise HTTPException(status_code=422, detail=f"袋名最多 {TAG_TITLE_MAX} 个字符")
    tag = session.get(AssetTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    tag.title = title
    session.commit()
    session.refresh(tag)
    return tag


@app.post("/api/v1/tags/{tag_id}/printed", response_model=TagRead)
def print_tag(tag_id: UUID, session: Session = Depends(get_session)) -> AssetTag:
    tag = session.get(AssetTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")
    tag.printed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(tag)
    return tag


@app.delete("/api/v1/assets/{asset_id}")
def delete_asset(asset_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    """The code is not recycled: deleting an asset leaves its sticker number dead."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    session.delete(asset)
    session.commit()
    return {"deleted": str(asset_id)}


@app.get("/api/v1/media/{video_id}")
def media(video_id: str, date: str | None = None) -> FileResponse:
    """Serve the downloaded mp4 so the review page can play it inline."""
    if not VIDEO_ID.match(video_id):
        raise HTTPException(status_code=404, detail="视频不存在")
    pattern = f"{date}_{video_id}/video/{video_id}.mp4" if date and DATE.match(date) else f"*_{video_id}/video/{video_id}.mp4"
    matches = sorted(MEDIA_ROOT.glob(pattern))
    if not matches:
        raise HTTPException(status_code=404, detail="本地视频未下载")
    return FileResponse(matches[-1], media_type="video/mp4", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/v1/products/{product_id}/review-items", response_model=list[ReviewItemRead])
def list_product_review_items(product_id: UUID, session: Session = Depends(get_session)) -> list[ReviewItem]:
    return list(session.scalars(
        select(ReviewItem)
        .where(ReviewItem.product_id == product_id)
        .order_by(ReviewItem.event_date.desc(), ReviewItem.created_at.desc())
    ))


@app.get("/api/v1/review/stats")
def review_stats(session: Session = Depends(get_session)) -> dict[str, int]:
    rows = session.execute(select(ReviewItem.state, func.count()).group_by(ReviewItem.state)).all()
    counts = {state: count for state, count in rows}
    later = session.scalar(
        select(func.count()).select_from(ReviewItem).where(
            ReviewItem.state == "skipped", ReviewItem.skip_reason == "later"
        )
    ) or 0
    total = sum(counts.values())
    return {
        "pending": counts.get("pending", 0),
        "mapped": counts.get("mapped", 0),
        "created": counts.get("created", 0),
        "skipped": counts.get("skipped", 0),
        "later": later,
        "total": total,
    }


@app.get("/api/v1/review/items", response_model=ReviewList)
def review_items(
    state: str = "pending",
    q: str | None = None,
    sort: str = "brand",
    limit: int = Query(default=30, le=200),
    offset: int = 0,
    session: Session = Depends(get_session),
) -> ReviewList:
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
        order = (ReviewItem.brand.nulls_last(), ReviewItem.product.nulls_last(), ReviewItem.event_date, ReviewItem.start_seconds)
    statement = base.order_by(*order).offset(offset).limit(limit)
    return ReviewList(total=total, items=list(session.scalars(statement)))


@app.post("/api/v1/review/{item_id}/map", response_model=ReviewItemRead)
def map_item(item_id: UUID, payload: ReviewMapRequest, session: Session = Depends(get_session)) -> ReviewItem:
    """Link the mention to an existing product; the product itself is untouched."""
    item = session.get(ReviewItem, item_id)
    if item is None or item.state != "pending":
        raise HTTPException(status_code=404, detail="待审核条目不存在或已处理")
    product = session.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="目标产品不存在")
    item.product_id = product.id
    item.state = "mapped"
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(item)
    return item


def find_duplicate(
    session: Session,
    manufacturer: str | None,
    kit_name: str,
    exclude_id: UUID | None = None,
) -> Product | None:
    statement = select(Product).where(Product.kit_name == kit_name)
    statement = statement.where(
        Product.manufacturer.is_(None) if manufacturer is None else Product.manufacturer == manufacturer
    )
    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)
    return session.scalar(statement)


@app.post("/api/v1/review/{item_id}/create", response_model=ProductRead)
def create_from_item(item_id: UUID, payload: ReviewCreateRequest, session: Session = Depends(get_session)) -> Product:
    item = session.get(ReviewItem, item_id)
    if item is None or item.state != "pending":
        raise HTTPException(status_code=404, detail="待审核条目不存在或已处理")
    kit_name = payload.kit_name.strip()
    if not kit_name:
        raise HTTPException(status_code=422, detail="产品名称不能为空")
    manufacturer = (payload.manufacturer or item.brand or None)
    duplicate = find_duplicate(session, manufacturer, kit_name)
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="已存在同名产品，请用「映射」而不是新建")
    source_url = f"https://www.bilibili.com/video/{item.video_id}" if item.video_id else "手动录入"
    product = Product(
        manufacturer=manufacturer,
        product_code=(payload.product_code.strip() if payload.product_code and payload.product_code.strip() else None),
        product_line=payload.product_line or item.line or None,
        kit_name=kit_name,
        detail=payload.detail or item.detail,
        source=source_url,
        price=(payload.price_text.strip() if payload.price_text and payload.price_text.strip() else None),
    )
    session.add(product)
    session.flush()
    item.product_id = product.id
    item.state = "created"
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(product)
    return product


@app.post("/api/v1/review/{item_id}/skip", response_model=ReviewItemRead)
def skip_item(item_id: UUID, payload: ReviewSkipRequest | None = None, session: Session = Depends(get_session)) -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="条目不存在")
    reason = (payload.reason if payload else "later")
    if reason not in SKIP_REASONS:
        raise HTTPException(status_code=422, detail=f"reason 必须是 {sorted(SKIP_REASONS)} 之一")
    item.state = "skipped"
    item.skip_reason = reason
    item.reviewed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(item)
    return item


@app.post("/api/v1/review/{item_id}/reset", response_model=ReviewItemRead)
def reset_item(item_id: UUID, session: Session = Depends(get_session)) -> ReviewItem:
    item = session.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="条目不存在")
    item.state = "pending"
    item.skip_reason = None
    item.product_id = None
    item.reviewed_at = None
    session.commit()
    session.refresh(item)
    return item
