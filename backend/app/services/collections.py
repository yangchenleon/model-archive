"""Collection rules: a human-defined list of existing catalog products.

There is no rule engine and no placeholder: adding a target means pointing at a
product that already exists. Progress is derived from ``assets`` on read, so the
collection never stores a second copy of "owned".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models import Asset, Collection, CollectionItem, Product
from app.schemas import (
    CollectionBulkAdd,
    CollectionBulkRemove,
    CollectionCreate,
    CollectionItemUpdate,
    CollectionStats,
    CollectionUpdate,
    ProductCollectionRead,
)
from app.services.errors import Conflict, Invalid, NotFound

STATUSES = ("planning", "active", "paused", "abandoned")
BULK_LIMIT = 500


@dataclass
class AssetRollup:
    owned: int = 0
    built: int = 0
    sold: int = 0
    states: list[str] = field(default_factory=list)


@dataclass
class ItemView:
    item: CollectionItem
    product: Product
    roll: AssetRollup


def ensure_status(status: str) -> str:
    if status not in STATUSES:
        raise Invalid(f"status 必须是 {list(STATUSES)} 之一")
    return status


def require(session: Session, collection_id: UUID) -> Collection:
    collection = session.get(Collection, collection_id)
    if collection is None:
        raise NotFound("收藏集不存在")
    return collection


def _require_product(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFound("产品不存在")
    return product


def _require_item(session: Session, collection_id: UUID, item_id: UUID) -> CollectionItem:
    item = session.get(CollectionItem, item_id)
    if item is None or item.collection_id != collection_id:
        raise NotFound("目标不存在")
    return item


def _unique_title(session: Session, title: str, exclude_id: UUID | None = None) -> None:
    statement = select(Collection).where(Collection.title == title)
    if exclude_id is not None:
        statement = statement.where(Collection.id != exclude_id)
    if session.scalar(statement) is not None:
        raise Conflict("已存在同名收藏集")


def _touch(collection: Collection) -> None:
    collection.updated_at = datetime.now(timezone.utc)


def _clean_text(value: str | None) -> str | None:
    return (value or "").strip() or None


def _rollup_assets(session: Session, product_ids: set[UUID]) -> dict[UUID, AssetRollup]:
    """One query for every product in the page; multi-copy counted once."""
    if not product_ids:
        return {}
    rows = session.execute(
        select(Asset.product_id, Asset.state, Asset.built_on)
        .where(Asset.product_id.in_(product_ids))
        .order_by(Asset.product_id, Asset.created_at)
    ).all()
    rolls: dict[UUID, AssetRollup] = {}
    for product_id, state, built_on in rows:
        roll = rolls.setdefault(product_id, AssetRollup())
        if state == "sold":
            roll.sold += 1
            continue
        roll.owned += 1
        if state in ("displayed", "stored") or built_on is not None:
            roll.built += 1
        if state not in roll.states:
            roll.states.append(state)
    return rolls


def _stats(items: list[CollectionItem], rolls: dict[UUID, AssetRollup]) -> CollectionStats:
    total = len(items)
    owned = built = sold_only = extra_copies = 0
    for item in items:
        roll = rolls.get(item.product_id, AssetRollup())
        if roll.owned:
            owned += 1
            if roll.built:
                built += 1
            extra_copies += max(0, roll.owned - 1)
        elif roll.sold:
            sold_only += 1
    missing = total - owned
    return CollectionStats(
        total=total,
        owned=owned,
        built=built,
        unbuilt=owned - built,
        missing=missing,
        sold_only=sold_only,
        extra_copies=extra_copies,
        percent=round(owned * 100 / total, 1) if total else 0,
        completed=total > 0 and owned == total,
    )


def stats_map(session: Session, collection_ids: list[UUID]) -> dict[UUID, CollectionStats]:
    result = {collection_id: CollectionStats() for collection_id in collection_ids}
    if not collection_ids:
        return result

    items = list(session.scalars(
        select(CollectionItem).where(CollectionItem.collection_id.in_(collection_ids))
    ))
    rolls = _rollup_assets(session, {item.product_id for item in items})
    grouped: dict[UUID, list[CollectionItem]] = {collection_id: [] for collection_id in collection_ids}
    for item in items:
        grouped.setdefault(item.collection_id, []).append(item)
    for collection_id, group in grouped.items():
        result[collection_id] = _stats(group, rolls)
    return result


def list_with_stats(
    session: Session,
    status: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> list[tuple[Collection, CollectionStats]]:
    statement = select(Collection).order_by(Collection.updated_at.desc(), Collection.title).limit(limit)
    if status and status != "all":
        ensure_status(status)
        statement = statement.where(Collection.status == status)
    if q and q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(or_(
            Collection.title.ilike(term),
            Collection.description.ilike(term),
        ))
    collections = list(session.scalars(statement))
    stats = stats_map(session, [collection.id for collection in collections])
    return [(collection, stats[collection.id]) for collection in collections]


def get_with_stats(session: Session, collection_id: UUID) -> tuple[Collection, CollectionStats]:
    collection = require(session, collection_id)
    return collection, stats_map(session, [collection_id])[collection_id]


def create(session: Session, payload: CollectionCreate) -> Collection:
    title = payload.title.strip()
    if not title:
        raise Invalid("收藏集名称不能为空")
    ensure_status(payload.status)
    _unique_title(session, title)

    collection = Collection(
        title=title,
        description=_clean_text(payload.description),
        status=payload.status,
        started_on=payload.started_on,
        target_on=payload.target_on,
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def update(session: Session, collection_id: UUID, payload: CollectionUpdate) -> Collection:
    collection = require(session, collection_id)
    data = payload.model_dump(exclude_unset=True)

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise Invalid("收藏集名称不能为空")
        _unique_title(session, title, exclude_id=collection.id)
        collection.title = title
    if "status" in data:
        ensure_status(data["status"])
        collection.status = data["status"]
    if "description" in data:
        collection.description = _clean_text(data["description"])
    if "started_on" in data:
        collection.started_on = data["started_on"]
    if "target_on" in data:
        collection.target_on = data["target_on"]

    _touch(collection)
    session.commit()
    session.refresh(collection)
    return collection


def delete(session: Session, collection_id: UUID) -> int:
    collection = require(session, collection_id)
    removed = session.scalar(
        select(func.count()).select_from(CollectionItem).where(CollectionItem.collection_id == collection_id)
    ) or 0
    session.delete(collection)
    session.commit()
    return removed


def _item_view(session: Session, item: CollectionItem) -> ItemView:
    product = item.product
    roll = _rollup_assets(session, {product.id}).get(product.id, AssetRollup())
    return ItemView(item=item, product=product, roll=roll)


def add_item(session: Session, collection_id: UUID, product_id: UUID) -> ItemView:
    collection = require(session, collection_id)
    product = _require_product(session, product_id)
    duplicate = session.scalar(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.product_id == product.id,
        )
    )
    if duplicate is not None:
        raise Conflict("该产品已在此收藏集中")

    item = CollectionItem(collection_id=collection.id, product_id=product.id)
    session.add(item)
    _touch(collection)
    session.commit()
    session.refresh(item)
    item.product = product
    return _item_view(session, item)


def add_many(session: Session, collection_id: UUID, payload: CollectionBulkAdd) -> dict[str, int]:
    collection = require(session, collection_id)
    product_ids = list(dict.fromkeys(payload.product_ids))
    if not product_ids:
        raise Invalid("至少选择一个产品")
    if len(product_ids) > BULK_LIMIT:
        raise Invalid(f"单次最多 {BULK_LIMIT} 条")

    known = set(session.scalars(select(Product.id).where(Product.id.in_(product_ids))))
    missing = [str(pid) for pid in product_ids if pid not in known]
    if missing:
        raise NotFound(f"产品不存在：{missing[0]}")

    existing = set(session.scalars(
        select(CollectionItem.product_id).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.product_id.in_(product_ids),
        )
    ))
    fresh = [pid for pid in product_ids if pid not in existing]
    session.add_all([
        CollectionItem(collection_id=collection.id, product_id=product_id)
        for product_id in fresh
    ])
    _touch(collection)
    session.commit()
    return {"added": len(fresh), "skipped": len(product_ids) - len(fresh)}


def remove_item(session: Session, collection_id: UUID, item_id: UUID) -> None:
    collection = require(session, collection_id)
    item = _require_item(session, collection_id, item_id)
    session.delete(item)
    _touch(collection)
    session.commit()


def remove_many(session: Session, collection_id: UUID, payload: CollectionBulkRemove) -> dict[str, int]:
    collection = require(session, collection_id)
    item_ids = list(dict.fromkeys(payload.item_ids))
    if not item_ids:
        raise Invalid("至少选择一个目标")
    items = list(session.scalars(
        select(CollectionItem).where(
            CollectionItem.collection_id == collection.id,
            CollectionItem.id.in_(item_ids),
        )
    ))
    found = {item.id for item in items}
    missing = [str(item_id) for item_id in item_ids if item_id not in found]
    if missing:
        raise NotFound(f"目标不存在：{missing[0]}")
    for item in items:
        session.delete(item)
    _touch(collection)
    session.commit()
    return {"removed": len(items)}


def update_item(
    session: Session,
    collection_id: UUID,
    item_id: UUID,
    payload: CollectionItemUpdate,
) -> ItemView:
    collection = require(session, collection_id)
    item = _require_item(session, collection_id, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "note" in data:
        item.note = _clean_text(data["note"])
        _touch(collection)
        session.commit()
        session.refresh(item)
    return _item_view(session, item)


def _item_matches(product: Product, term: str) -> bool:
    haystack = " ".join(filter(None, [
        product.kit_name,
        product.product_code,
        product.manufacturer,
        product.product_line,
    ])).lower()
    return term in haystack


def list_items(
    session: Session,
    collection_id: UUID,
    state: str = "all",
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[int, list[ItemView]]:
    require(session, collection_id)
    if state not in {"all", "owned", "missing"}:
        raise Invalid("state 必须是 all / owned / missing 之一")

    items = list(session.scalars(
        select(CollectionItem)
        .join(CollectionItem.product)
        .options(contains_eager(CollectionItem.product))
        .where(CollectionItem.collection_id == collection_id)
        .order_by(
            Product.product_line.nulls_last(),
            Product.product_code.nulls_last(),
            Product.kit_name,
        )
    ))
    rolls = _rollup_assets(session, {item.product_id for item in items})
    term = (q or "").strip().lower()

    filtered: list[ItemView] = []
    for item in items:
        roll = rolls.get(item.product_id, AssetRollup())
        if state == "owned" and not roll.owned:
            continue
        if state == "missing" and roll.owned:
            continue
        if term and not _item_matches(item.product, term):
            continue
        filtered.append(ItemView(item=item, product=item.product, roll=roll))

    total = len(filtered)
    return total, filtered[offset:offset + limit]


def product_collections(session: Session, product_id: UUID) -> list[ProductCollectionRead]:
    _require_product(session, product_id)
    owned = (session.scalar(
        select(func.count()).select_from(Asset).where(
            Asset.product_id == product_id,
            Asset.state != "sold",
        )
    ) or 0) > 0
    collections = list(session.scalars(
        select(Collection)
        .join(CollectionItem, CollectionItem.collection_id == Collection.id)
        .where(CollectionItem.product_id == product_id)
        .order_by(Collection.updated_at.desc(), Collection.title)
    ))
    return [
        ProductCollectionRead(id=collection.id, title=collection.title, owned=owned)
        for collection in collections
    ]
