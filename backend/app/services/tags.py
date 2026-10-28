"""Tag rules: one sticker per bag, codes derived from the asset code.

A tag is a physical sticker. Printing is the only event the system can observe,
so ``printed_at`` is driven by the print action and a reprint is the same
sticker — the code never changes because the bag did not change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Asset, AssetTag, Product
from app.schemas import BulkTagCreate, TagQueueItem
from app.services import assets as assets_service
from app.services import codes
from app.services.errors import Invalid, NotFound

TITLE_MAX = 24
DEFAULT_TITLE = "本体"


def clean_title(title: str | None) -> str:
    value = (title or "").strip() or DEFAULT_TITLE
    if len(value) > TITLE_MAX:
        raise Invalid(f"袋名最多 {TITLE_MAX} 个字符")
    return value


def _require_tag(session: Session, tag_id: UUID) -> AssetTag:
    tag = session.get(AssetTag, tag_id)
    if tag is None:
        raise NotFound("标签不存在")
    return tag


def issue(session: Session, asset_id: UUID, title: str | None) -> AssetTag:
    """Add one more bag to an asset; the next free seq picks the suffix."""
    value = clean_title(title)
    asset = assets_service.load(session, asset_id)
    last_seq = session.scalar(select(func.max(AssetTag.seq)).where(AssetTag.asset_id == asset.id)) or 0
    seq = last_seq + 1
    tag = AssetTag(asset_id=asset.id, seq=seq, code=codes.issue(session, 1)[0], title=value)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


def requeue(session: Session, payload: BulkTagCreate) -> list[AssetTag]:
    """Put the selected assets back in the print queue.

    An asset without a sticker gets one; an asset that already has stickers has
    them marked unprinted again, keeping their codes — a reprint is the same
    sticker, and the asset page does not need to know which case it hit.
    """
    value = clean_title(payload.title)
    assets = list(session.scalars(
        select(Asset).where(Asset.id.in_(payload.asset_ids)).options(selectinload(Asset.tags))
    ))
    found = {asset.id for asset in assets}
    missing = [str(aid) for aid in payload.asset_ids if aid not in found]
    if missing:
        raise NotFound(f"资产不存在：{missing[0]}")

    fresh = [asset for asset in assets if not asset.tags]
    issued = codes.issue(session, len(fresh))
    session.add_all([
        AssetTag(asset_id=asset.id, seq=1, code=code, title=value)
        for asset, code in zip(fresh, issued)
    ])

    for asset in assets:
        for tag in asset.tags:
            tag.printed_at = None

    session.commit()
    return list(session.scalars(
        select(AssetTag)
        .where(AssetTag.asset_id.in_([asset.id for asset in assets]))
        .order_by(AssetTag.created_at, AssetTag.code)
    ))


def rename(session: Session, tag_id: UUID, title: str) -> AssetTag:
    """Renaming is cheap and keeps the code, so no sticker is wasted."""
    value = (title or "").strip()
    if not value:
        raise Invalid("袋名不能为空")
    if len(value) > TITLE_MAX:
        raise Invalid(f"袋名最多 {TITLE_MAX} 个字符")
    tag = _require_tag(session, tag_id)
    tag.title = value
    session.commit()
    session.refresh(tag)
    return tag


def mark_printed(session: Session, tag_id: UUID) -> AssetTag:
    tag = _require_tag(session, tag_id)
    tag.printed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(tag)
    return tag


def mark_many_printed(session: Session, tag_ids: list[UUID]) -> dict[str, int]:
    """Called by the print page: moving the stamp forward also covers reprints."""
    now = datetime.now(timezone.utc)
    tags = list(session.scalars(select(AssetTag).where(AssetTag.id.in_(tag_ids))))
    for tag in tags:
        tag.printed_at = now
    session.commit()
    return {"requested": len(tag_ids), "printed": len(tags)}


def queue(session: Session, status: str, limit: int) -> list[TagQueueItem]:
    """``open`` is the print queue; ``printed`` is where damaged stickers are found again."""
    statement = (
        select(AssetTag, Asset, Product)
        .join(Asset, AssetTag.asset_id == Asset.id)
        .join(Product, Asset.product_id == Product.id)
        .order_by(AssetTag.created_at, AssetTag.code)
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
