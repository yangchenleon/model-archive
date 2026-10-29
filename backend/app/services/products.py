"""Product catalogue rules: identity, duplicate detection, bulk atomicity."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.channels import RELEASE_CHANNELS
from app.models import Manufacturer, Product, ProductLine, ReviewItem
from app.schemas import ProductCreate, ProductUpdate
from app.services.errors import Conflict, Invalid, NotFound

BULK_LIMIT = 500


def _require_manufacturer(session: Session, manufacturer_id: UUID) -> Manufacturer:
    manufacturer = session.get(Manufacturer, manufacturer_id)
    if manufacturer is None:
        raise NotFound("厂商不存在")
    return manufacturer


def require_line(session: Session, line_id: UUID, manufacturer_id: UUID) -> ProductLine:
    line = session.get(ProductLine, line_id)
    if line is None:
        raise NotFound("产品线不存在")
    if line.manufacturer_id != manufacturer_id:
        raise Invalid("产品线不属于该厂商")
    return line


def find_duplicate(
    session: Session,
    manufacturer_id: UUID,
    product_line_id: UUID | None,
    kit_name: str,
    exclude_id: UUID | None = None,
) -> Product | None:
    """Identity is (manufacturer_id, product_line_id, kit_name).

    A NULL line is its own bucket: an unknown-line product only matches another
    unknown-line product, not a product in a named line.
    """
    line_match = (
        Product.product_line_id.is_(None)
        if product_line_id is None
        else Product.product_line_id == product_line_id
    )
    statement = select(Product).where(
        Product.manufacturer_id == manufacturer_id,
        line_match,
        Product.kit_name == kit_name,
    )
    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)
    return session.scalar(statement)


def require(session: Session, product_id: UUID) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise NotFound("产品不存在")
    return product


def _validate_channel(channel: str | None) -> None:
    if channel is not None and channel not in RELEASE_CHANNELS:
        raise Invalid(f"release_channel 必须是 {list(RELEASE_CHANNELS)} 或 null")


def _validate_line(session: Session, manufacturer_id: UUID, line_id: UUID | None) -> None:
    if line_id is not None:
        require_line(session, line_id, manufacturer_id)


def create(session: Session, payload: ProductCreate) -> Product:
    kit_name = payload.kit_name.strip()
    if not kit_name:
        raise Invalid("产品名称不能为空")
    _require_manufacturer(session, payload.manufacturer_id)
    _validate_line(session, payload.manufacturer_id, payload.product_line_id)
    _validate_channel(payload.release_channel)
    if find_duplicate(
        session, payload.manufacturer_id, payload.product_line_id, kit_name
    ) is not None:
        raise Conflict("已存在同厂商同系列下的同名产品")
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

    seen: set[tuple[UUID, UUID | None, str]] = set()
    products: list[Product] = []
    for index, item in enumerate(payloads, start=1):
        kit_name = item.kit_name.strip()
        if not kit_name:
            raise Invalid(f"第 {index} 条产品名称为空")
        _require_manufacturer(session, item.manufacturer_id)
        _validate_line(session, item.manufacturer_id, item.product_line_id)
        _validate_channel(item.release_channel)
        key = (item.manufacturer_id, item.product_line_id, kit_name)
        if key in seen:
            raise Conflict(f"第 {index} 条与本次提交内的产品重复：{kit_name}")
        if find_duplicate(
            session, item.manufacturer_id, item.product_line_id, kit_name
        ) is not None:
            raise Conflict(f"第 {index} 条已存在同厂商同系列同名产品：{kit_name}")
        seen.add(key)
        product = Product(**{**item.model_dump(), "kit_name": kit_name})
        session.add(product)
        products.append(product)

    session.commit()
    for product in products:
        session.refresh(product)
    return products


def set_channel_many(session: Session, product_ids: list[UUID], channel: str | None) -> int:
    if not product_ids:
        raise Invalid("至少选择一条产品")
    if len(product_ids) > BULK_LIMIT:
        raise Invalid(f"单次最多 {BULK_LIMIT} 条")
    _validate_channel(channel)
    result = session.execute(
        update(Product)
        .where(Product.id.in_(product_ids))
        .values(release_channel=channel)
    )
    session.commit()
    return result.rowcount or 0


def update_product(session: Session, product_id: UUID, payload: ProductUpdate) -> Product:
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

    manufacturer_id = data.get("manufacturer_id", product.manufacturer_id)
    if manufacturer_id is None:
        raise Invalid("厂商不能为空")
    _require_manufacturer(session, manufacturer_id)

    if "release_channel" in data:
        _validate_channel(data["release_channel"])

    target_line_id = data.get("product_line_id", product.product_line_id)
    if "product_line_id" in data:
        _validate_line(session, manufacturer_id, data["product_line_id"])
    elif manufacturer_id != product.manufacturer_id and product.product_line_id:
        # The old line belongs to the old manufacturer; a cross-maker line is invalid.
        line = session.get(ProductLine, product.product_line_id)
        if line is None or line.manufacturer_id != manufacturer_id:
            target_line_id = None
            data["product_line_id"] = None

    duplicate = find_duplicate(
        session,
        manufacturer_id,
        target_line_id,
        data.get("kit_name", product.kit_name),
        exclude_id=product.id,
    )
    if duplicate is not None:
        raise Conflict("已存在同厂商同系列下的同名产品")

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
            .values(
                state="pending",
                product_id=None,
                manufacturer_id=None,
                product_line_id=None,
                skip_reason=None,
                reviewed_at=None,
            )
        )
    session.delete(product)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise Conflict("该产品仍被资产引用，无法删除")
    return {"deleted": str(product_id), "review_items_reset": linked}
