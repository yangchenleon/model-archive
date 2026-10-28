"""Asset rules: one row per owned kit, state transitions and their audit."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Asset, AssetStateChange, AssetTag, Product
from app.schemas import AssetCreate, AssetUpdate, BulkAssetCreate, BulkStateUpdate
from app.services import codes
from app.services.errors import Invalid, NotFound

STATES = {"pending", "keep", "displayed", "stored", "sold"}
BULK_LIMIT = 200


def ensure_state(state: str) -> str:
    if state not in STATES:
        raise Invalid(f"state 必须是 {sorted(STATES)} 之一")
    return state


def load(session: Session, asset_id: UUID) -> Asset:
    asset = session.scalar(
        select(Asset)
        .where(Asset.id == asset_id)
        .options(selectinload(Asset.product), selectinload(Asset.tags))
    )
    if asset is None:
        raise NotFound("资产不存在")
    return asset


def _require_product(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFound("产品不存在")
    return product


def find_by_code(session: Session, raw: str) -> Asset:
    """Resolve a code typed or scanned from a sticker.

    A second bag carries ``<asset>-2``; scanning that should still land on the
    asset, because the asset is what the page shows.
    """
    code = codes.normalise(raw)
    asset = session.scalar(
        select(Asset).where(Asset.code == code).options(selectinload(Asset.product), selectinload(Asset.tags))
    )
    if asset is None:
        tag = session.scalar(select(AssetTag).where(AssetTag.code == code))
        if tag is not None:
            asset = load(session, tag.asset_id)
    if asset is None:
        raise NotFound("没有这个编号")
    return asset


def create(session: Session, payload: AssetCreate) -> Asset:
    """Buying the same kit twice means two rows; there is no quantity column."""
    ensure_state(payload.state)
    product = _require_product(session, payload.product_id)
    asset = Asset(
        product_id=product.id,
        code=codes.issue(session, 1)[0],
        **payload.model_dump(exclude={"product_id"}),
    )
    session.add(asset)
    session.flush()
    session.add(AssetStateChange(asset_id=asset.id, from_state=None, to_state=asset.state))
    session.commit()
    session.refresh(asset)
    _ = asset.product, asset.tags
    return asset


def create_many(session: Session, payload: BulkAssetCreate) -> list[Asset]:
    """Backlog entry: register N products at once, each with an initial state."""
    ensure_state(payload.state)
    if not payload.product_ids:
        raise Invalid("至少选择一个产品")
    if len(payload.product_ids) > BULK_LIMIT:
        raise Invalid(f"单次最多 {BULK_LIMIT} 条")

    known = set(session.scalars(select(Product.id).where(Product.id.in_(payload.product_ids))))
    missing = [str(pid) for pid in payload.product_ids if pid not in known]
    if missing:
        raise NotFound(f"产品不存在：{missing[0]}")

    issued = codes.issue(session, len(payload.product_ids))
    assets = [
        Asset(product_id=pid, code=code, state=payload.state, acquired_on=payload.acquired_on)
        for pid, code in zip(payload.product_ids, issued)
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


def update(session: Session, asset_id: UUID, payload: AssetUpdate) -> Asset:
    """Field edits are silent; a state change also appends an audit row."""
    asset = load(session, asset_id)
    data = payload.model_dump(exclude_unset=True)

    new_state = data.get("state")
    if new_state is not None:
        ensure_state(new_state)
        if new_state != asset.state:
            session.add(AssetStateChange(asset_id=asset.id, from_state=asset.state, to_state=new_state))
            asset.state = new_state
        data.pop("state")

    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(asset, field, value)
    session.commit()
    session.refresh(asset)
    _ = asset.product, asset.tags
    return asset


def change_many(session: Session, payload: BulkStateUpdate) -> dict[str, int]:
    """One transition for many assets; assets already in that state are skipped."""
    ensure_state(payload.state)
    assets = list(session.scalars(
        select(Asset).where(Asset.id.in_(payload.asset_ids)).options(selectinload(Asset.tags))
    ))
    found = {asset.id for asset in assets}
    missing = [str(aid) for aid in payload.asset_ids if aid not in found]
    if missing:
        raise NotFound(f"资产不存在：{missing[0]}")

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


def delete(session: Session, asset_id: UUID) -> None:
    """Codes are not recycled: deleting an asset leaves its sticker number dead."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise NotFound("资产不存在")
    session.delete(asset)
    session.commit()


def history(session: Session, asset_id: UUID) -> list[AssetStateChange]:
    if session.get(Asset, asset_id) is None:
        raise NotFound("资产不存在")
    return list(session.scalars(
        select(AssetStateChange)
        .where(AssetStateChange.asset_id == asset_id)
        .order_by(AssetStateChange.changed_at, AssetStateChange.id)
    ))
