"""Product catalogue endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Manufacturer, Product, ProductLine
from app.schemas import ProductCollectionRead, ProductCreate, ProductRead, ProductUpdate
from app.services import collections as collection_service
from app.services import products as service

router = APIRouter(tags=["products"])


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)) -> Product:
    return service.create(session, payload)


@router.post("/products/bulk", response_model=list[ProductRead], status_code=status.HTTP_201_CREATED)
def bulk_create_products(payload: list[ProductCreate], session: Session = Depends(get_session)) -> list[Product]:
    """CSV/JSON importers live outside the project; they call this with clean values."""
    return service.create_many(session, payload)


@router.get("/products", response_model=list[ProductRead])
def list_products(
    search: str | None = None,
    limit: int = Query(default=100, le=2000),
    session: Session = Depends(get_session),
) -> list[Product]:
    statement = (
        select(Product)
        .join(Manufacturer, Product.manufacturer_id == Manufacturer.id)
        .outerjoin(ProductLine, Product.product_line_id == ProductLine.id)
        .order_by(
            Manufacturer.name.nulls_last(),
            ProductLine.name.nulls_last(),
            Product.product_code.nulls_last(),
            Product.kit_name,
        )
        .limit(limit)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(
            Product.kit_name.ilike(term),
            Manufacturer.name.ilike(term),
            ProductLine.name.ilike(term),
            Product.product_code.ilike(term),
        ))
    return list(session.scalars(statement))


@router.get("/products/{product_id}/collections", response_model=list[ProductCollectionRead])
def list_product_collections(
    product_id: UUID,
    session: Session = Depends(get_session),
) -> list[ProductCollectionRead]:
    """Which collections include this product, and whether it is currently owned."""
    return collection_service.product_collections(session, product_id)


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: UUID, session: Session = Depends(get_session)) -> Product:
    return service.require(session, product_id)


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(product_id: UUID, payload: ProductUpdate, session: Session = Depends(get_session)) -> Product:
    return service.update(session, product_id, payload)


@router.delete("/products/{product_id}")
def delete_product(product_id: UUID, session: Session = Depends(get_session)) -> dict[str, str | int]:
    return service.delete(session, product_id)
