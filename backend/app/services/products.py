"""Product catalogue rules: identity, duplicate detection, bulk atomicity."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Product, ReviewItem
from app.schemas import ProductCreate, ProductUpdate
from app.services.errors import Conflict, Invalid, NotFound

BULK_LIMIT = 500


def find_duplicate(
    session: Session,
    manufacturer: str | None,
    kit_name: str,
    exclude_id: UUID | None = None,
) -> Product | None:
    """Identity is (manufacturer, kit_name); a missing maker only matches absence."""
    statement = select(Product).where(Product.kit_name == kit_name)
    statement = statement.where(
        Product.manufacturer.is_(None) if manufacturer is None else Product.manufacturer == manufacturer
    )
    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)
    return session.scalar(statement)


def require(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFound("产品不存在")
    return product


def create(session: Session, payload: ProductCreate) -> Product:
    kit_name = payload.kit_name.strip()
    if not kit_name:
        raise Invalid("产品名称不能为空")
    if find_duplicate(session, payload.manufacturer, kit_name) is not None:
        raise Conflict("已存在同名同厂商产品")
    product = Product(**{**payload.model_dump(), "kit_name": kit_name})
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def create_many(session: Session, payloads: list[ProductCreate]) -> list[Product]:
    """All-or-nothing: any duplicate aborts the batch instead of inserting part of it."""
    if not payloads:
        raise Invalid("至少提交一条产品")
    if len(payloads) > BULK_LIMIT:
        raise Invalid(f"单次最多 {BULK_LIMIT} 条")

    seen: set[tuple[str | None, str]] = set()
    products: list[Product] = []
    for index, item in enumerate(payloads, start=1):
        kit_name = item.kit_name.strip()
        if not kit_name:
            raise Invalid(f"第 {index} 条产品名称为空")
        key = (item.manufacturer, kit_name)
        if key in seen:
            raise Conflict(f"第 {index} 条与本次提交内的产品重复：{kit_name}")
        if find_duplicate(session, item.manufacturer, kit_name) is not None:
            raise Conflict(f"第 {index} 条已存在同名同厂商产品：{kit_name}")
        seen.add(key)
        product = Product(**{**item.model_dump(), "kit_name": kit_name})
        session.add(product)
        products.append(product)

    session.commit()
    for product in products:
        session.refresh(product)
    return products


def update(session: Session, product_id: UUID, payload: ProductUpdate) -> Product:
    product = require(session, product_id)
    data = payload.model_dump(exclude_unset=True)

    if "kit_name" in data:
        name = (data["kit_name"] or "").strip()
        if not name:
            raise Invalid("产品名称不能为空")
        data["kit_name"] = name
    if "source" in data:
        source = (data["source"] or "").strip()
        if not source:
            raise Invalid("资料来源不能为空")
        data["source"] = source

    duplicate = find_duplicate(
        session,
        data.get("manufacturer", product.manufacturer),
        data.get("kit_name", product.kit_name),
        exclude_id=product.id,
    )
    if duplicate is not None:
        raise Conflict("已存在同名同厂商产品")

    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(product, field, value)
    session.commit()
    session.refresh(product)
    return product


def delete(session: Session, product_id: UUID) -> dict[str, str | int]:
    """Deleting a product returns its review items to the queue.

    There is no timeline to cascade; the only cross-table effect is that audit
    rows must not stay mapped to a row that no longer exists.
    """
    product = require(session, product_id)
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
        raise Conflict("该产品仍被资产引用，无法删除")
    return {"deleted": str(product_id), "review_items_reset": linked}
