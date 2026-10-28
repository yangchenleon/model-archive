"""Manufacturer and product-line rules.

Manufacturers are the primary taxonomy. A line belongs to one manufacturer and
is deliberately flat: HG, HGUC and HG GTO are separate lines, not a hierarchy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import Manufacturer, Product, ProductLine, ReviewItem
from app.schemas import (
    ManufacturerCreate,
    ManufacturerRead,
    ManufacturerUpdate,
    ProductLineCreate,
    ProductLineRead,
    ProductLineUpdate,
)
from app.services.errors import Conflict, Invalid, NotFound

CATEGORIES = ("gundam", "guomo", "ko")
TIERS = (1, 2, 3)
LINE_UNKNOWN = "未知"


def ensure_category(category: str | None) -> None:
    if category is not None and category not in CATEGORIES:
        raise Invalid(f"category 必须是 {list(CATEGORIES)} 或 null")


def ensure_tier(tier: int | None) -> None:
    if tier is not None and tier not in TIERS:
        raise Invalid(f"tier 必须是 {list(TIERS)} 之一")


def require_manufacturer(session: Session, manufacturer_id: UUID) -> Manufacturer:
    manufacturer = session.get(Manufacturer, manufacturer_id)
    if manufacturer is None:
        raise NotFound("厂商不存在")
    return manufacturer


def require_line(session: Session, line_id: UUID) -> ProductLine:
    line = session.get(ProductLine, line_id)
    if line is None:
        raise NotFound("产品线不存在")
    return line


def _touch(manufacturer: Manufacturer) -> None:
    manufacturer.updated_at = datetime.now(timezone.utc)


def _touch_line(line: ProductLine) -> None:
    line.updated_at = datetime.now(timezone.utc)


def _unique_name(session: Session, name: str, exclude_id: UUID | None = None) -> None:
    statement = select(Manufacturer).where(Manufacturer.name == name)
    if exclude_id is not None:
        statement = statement.where(Manufacturer.id != exclude_id)
    if session.scalar(statement) is not None:
        raise Conflict("已存在同名厂商")


def _product_counts(session: Session) -> dict[UUID, int]:
    return dict(session.execute(
        select(Product.manufacturer_id, func.count()).group_by(Product.manufacturer_id)
    ).all())


def _line_counts(session: Session) -> dict[UUID, int]:
    return dict(session.execute(
        select(ProductLine.manufacturer_id, func.count()).group_by(ProductLine.manufacturer_id)
    ).all())


def manufacturer_read(
    manufacturer: Manufacturer,
    product_count: int = 0,
    line_count: int = 0,
) -> ManufacturerRead:
    return ManufacturerRead(
        id=manufacturer.id,
        name=manufacturer.name,
        category=manufacturer.category,
        tier=manufacturer.tier,
        sort_order=manufacturer.sort_order,
        description=manufacturer.description,
        product_count=product_count,
        line_count=line_count,
        created_at=manufacturer.created_at,
        updated_at=manufacturer.updated_at,
    )


def list_manufacturers(
    session: Session,
    category: str | None = None,
    q: str | None = None,
    limit: int = 500,
) -> list[tuple[Manufacturer, int, int]]:
    statement = select(Manufacturer).order_by(
        Manufacturer.category.nulls_last(),
        Manufacturer.tier,
        Manufacturer.sort_order,
        Manufacturer.name,
    ).limit(limit)
    if category:
        ensure_category(category)
        statement = statement.where(Manufacturer.category == category)
    if q and q.strip():
        statement = statement.where(Manufacturer.name.ilike(f"%{q.strip()}%"))
    manufacturers = list(session.scalars(statement))
    product_counts = _product_counts(session)
    line_counts = _line_counts(session)
    return [
        (manufacturer, product_counts.get(manufacturer.id, 0), line_counts.get(manufacturer.id, 0))
        for manufacturer in manufacturers
    ]


def get_manufacturer(session: Session, manufacturer_id: UUID) -> tuple[Manufacturer, int, int]:
    manufacturer = require_manufacturer(session, manufacturer_id)
    product_count = session.scalar(
        select(func.count()).select_from(Product).where(Product.manufacturer_id == manufacturer_id)
    ) or 0
    line_count = session.scalar(
        select(func.count()).select_from(ProductLine).where(ProductLine.manufacturer_id == manufacturer_id)
    ) or 0
    return manufacturer, product_count, line_count


def create_manufacturer(session: Session, payload: ManufacturerCreate) -> Manufacturer:
    name = payload.name.strip()
    if not name:
        raise Invalid("厂商名称不能为空")
    ensure_category(payload.category)
    ensure_tier(payload.tier)
    _unique_name(session, name)
    manufacturer = Manufacturer(
        name=name,
        category=payload.category,
        tier=payload.tier,
        sort_order=payload.sort_order,
        description=(payload.description or "").strip() or None,
    )
    session.add(manufacturer)
    session.commit()
    session.refresh(manufacturer)
    return manufacturer


def update_manufacturer(
    session: Session,
    manufacturer_id: UUID,
    payload: ManufacturerUpdate,
) -> Manufacturer:
    manufacturer = require_manufacturer(session, manufacturer_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise Invalid("厂商名称不能为空")
        _unique_name(session, name, exclude_id=manufacturer.id)
        manufacturer.name = name
    if "category" in data:
        ensure_category(data["category"])
        manufacturer.category = data["category"]
    if "tier" in data:
        if data["tier"] is None:
            raise Invalid("tier 不能为空")
        ensure_tier(data["tier"])
        manufacturer.tier = data["tier"]
    if "sort_order" in data:
        manufacturer.sort_order = data["sort_order"] or 0
    if "description" in data:
        manufacturer.description = (data["description"] or "").strip() or None

    _touch(manufacturer)
    session.commit()
    session.refresh(manufacturer)
    return manufacturer


def delete_manufacturer(session: Session, manufacturer_id: UUID) -> None:
    manufacturer = require_manufacturer(session, manufacturer_id)
    product_count = session.scalar(
        select(func.count()).select_from(Product).where(Product.manufacturer_id == manufacturer_id)
    ) or 0
    if product_count:
        raise Conflict(f"该厂商还有 {product_count} 款产品，请先合并到其他厂商")
    session.delete(manufacturer)
    session.commit()


def merge_manufacturer(session: Session, source_id: UUID, target_id: UUID) -> Manufacturer:
    """Move products/lines/review links from source to target, then remove source."""
    if source_id == target_id:
        raise Invalid("不能合并到自身")
    source = require_manufacturer(session, source_id)
    target = require_manufacturer(session, target_id)

    collisions = session.scalar(
        select(func.count()).select_from(Product).where(
            Product.manufacturer_id == source.id,
            Product.kit_name.in_(
                select(Product.kit_name).where(Product.manufacturer_id == target.id)
            ),
        )
    ) or 0
    if collisions:
        raise Conflict(f"两个厂商有 {collisions} 个同名产品，先改名或去重再合并")

    source_lines = list(session.scalars(
        select(ProductLine).where(ProductLine.manufacturer_id == source.id)
    ))
    for line in source_lines:
        target_line = session.scalar(
            select(ProductLine).where(
                ProductLine.manufacturer_id == target.id,
                ProductLine.name == line.name,
            )
        )
        if target_line is not None:
            session.execute(
                update(Product)
                .where(Product.product_line_id == line.id)
                .values(product_line_id=target_line.id)
            )
            session.execute(
                update(ReviewItem)
                .where(ReviewItem.product_line_id == line.id)
                .values(product_line_id=target_line.id)
            )
            session.delete(line)
        else:
            line.manufacturer_id = target.id

    session.execute(
        update(Product).where(Product.manufacturer_id == source.id).values(manufacturer_id=target.id)
    )
    session.execute(
        update(ReviewItem).where(ReviewItem.manufacturer_id == source.id).values(manufacturer_id=target.id)
    )
    session.execute(delete(Manufacturer).where(Manufacturer.id == source.id))
    _touch(target)
    session.commit()
    session.refresh(target)
    return target


def list_lines(
    session: Session,
    manufacturer_id: UUID | None = None,
    q: str | None = None,
    limit: int = 500,
) -> list[tuple[ProductLine, int]]:
    statement = select(ProductLine).order_by(
        ProductLine.manufacturer_id, ProductLine.sort_order, ProductLine.name
    ).limit(limit)
    if manufacturer_id is not None:
        require_manufacturer(session, manufacturer_id)
        statement = statement.where(ProductLine.manufacturer_id == manufacturer_id)
    if q and q.strip():
        statement = statement.where(ProductLine.name.ilike(f"%{q.strip()}%"))
    lines = list(session.scalars(statement))
    counts = dict(session.execute(
        select(Product.product_line_id, func.count())
        .where(Product.product_line_id.is_not(None))
        .group_by(Product.product_line_id)
    ).all())
    return [(line, counts.get(line.id, 0)) for line in lines]


def line_read(line: ProductLine, product_count: int = 0) -> ProductLineRead:
    return ProductLineRead(
        id=line.id,
        manufacturer_id=line.manufacturer_id,
        name=line.name,
        sort_order=line.sort_order,
        product_count=product_count,
    )


def create_line(session: Session, payload: ProductLineCreate) -> ProductLine:
    manufacturer = require_manufacturer(session, payload.manufacturer_id)
    name = payload.name.strip()
    if not name:
        raise Invalid("系列名称不能为空")
    duplicate = session.scalar(
        select(ProductLine).where(
            ProductLine.manufacturer_id == manufacturer.id,
            ProductLine.name == name,
        )
    )
    if duplicate is not None:
        raise Conflict("该厂商下已存在同名系列")
    line = ProductLine(
        manufacturer_id=manufacturer.id,
        name=name,
        sort_order=payload.sort_order,
    )
    session.add(line)
    session.commit()
    session.refresh(line)
    return line


def update_line(session: Session, line_id: UUID, payload: ProductLineUpdate) -> ProductLine:
    line = require_line(session, line_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise Invalid("系列名称不能为空")
        duplicate = session.scalar(
            select(ProductLine).where(
                ProductLine.manufacturer_id == line.manufacturer_id,
                ProductLine.name == name,
                ProductLine.id != line.id,
            )
        )
        if duplicate is not None:
            raise Conflict("该厂商下已存在同名系列")
        line.name = name
    if "sort_order" in data:
        line.sort_order = data["sort_order"] or 0
    _touch_line(line)
    session.commit()
    session.refresh(line)
    return line


def delete_line(session: Session, line_id: UUID) -> int:
    line = require_line(session, line_id)
    affected = session.scalar(
        select(func.count()).select_from(Product).where(Product.product_line_id == line.id)
    ) or 0
    session.execute(
        update(Product).where(Product.product_line_id == line.id).values(product_line_id=None)
    )
    session.execute(
        update(ReviewItem).where(ReviewItem.product_line_id == line.id).values(product_line_id=None)
    )
    session.delete(line)
    session.commit()
    return affected
