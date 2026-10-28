"""Manufacturer and product-line admin endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import (
    ManufacturerCreate,
    ManufacturerMergeRequest,
    ManufacturerRead,
    ManufacturerUpdate,
    ProductLineCreate,
    ProductLineRead,
    ProductLineUpdate,
)
from app.services import manufacturers as service

router = APIRouter(tags=["taxonomy"])


@router.get("/manufacturers", response_model=list[ManufacturerRead])
def list_manufacturers(
    category: str | None = None,
    q: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[ManufacturerRead]:
    return [
        service.manufacturer_read(manufacturer, products, lines)
        for manufacturer, products, lines in service.list_manufacturers(session, category, q, limit)
    ]


@router.post("/manufacturers", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    session: Session = Depends(get_session),
) -> ManufacturerRead:
    manufacturer = service.create_manufacturer(session, payload)
    return service.manufacturer_read(manufacturer)


@router.get("/manufacturers/{manufacturer_id}", response_model=ManufacturerRead)
def get_manufacturer(manufacturer_id: UUID, session: Session = Depends(get_session)) -> ManufacturerRead:
    manufacturer, products, lines = service.get_manufacturer(session, manufacturer_id)
    return service.manufacturer_read(manufacturer, products, lines)


@router.patch("/manufacturers/{manufacturer_id}", response_model=ManufacturerRead)
def update_manufacturer(
    manufacturer_id: UUID,
    payload: ManufacturerUpdate,
    session: Session = Depends(get_session),
) -> ManufacturerRead:
    manufacturer = service.update_manufacturer(session, manufacturer_id, payload)
    _, products, lines = service.get_manufacturer(session, manufacturer_id)
    return service.manufacturer_read(manufacturer, products, lines)


@router.delete("/manufacturers/{manufacturer_id}")
def delete_manufacturer(manufacturer_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    service.delete_manufacturer(session, manufacturer_id)
    return {"deleted": str(manufacturer_id)}


@router.post("/manufacturers/{manufacturer_id}/merge", response_model=ManufacturerRead)
def merge_manufacturer(
    manufacturer_id: UUID,
    payload: ManufacturerMergeRequest,
    session: Session = Depends(get_session),
) -> ManufacturerRead:
    target = service.merge_manufacturer(session, manufacturer_id, payload.target_id)
    _, products, lines = service.get_manufacturer(session, target.id)
    return service.manufacturer_read(target, products, lines)


@router.get("/product-lines", response_model=list[ProductLineRead])
def list_product_lines(
    manufacturer_id: UUID | None = None,
    q: str | None = None,
    limit: int = Query(default=500, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[ProductLineRead]:
    return [
        service.line_read(line, count)
        for line, count in service.list_lines(session, manufacturer_id, q, limit)
    ]


@router.post("/product-lines", response_model=ProductLineRead, status_code=status.HTTP_201_CREATED)
def create_product_line(
    payload: ProductLineCreate,
    session: Session = Depends(get_session),
) -> ProductLineRead:
    line = service.create_line(session, payload)
    return service.line_read(line)


@router.patch("/product-lines/{line_id}", response_model=ProductLineRead)
def update_product_line(
    line_id: UUID,
    payload: ProductLineUpdate,
    session: Session = Depends(get_session),
) -> ProductLineRead:
    line = service.update_line(session, line_id, payload)
    count = next((count for item, count in service.list_lines(session, line.manufacturer_id) if item.id == line.id), 0)
    return service.line_read(line, count)


@router.delete("/product-lines/{line_id}")
def delete_product_line(line_id: UUID, session: Session = Depends(get_session)) -> dict[str, str | int]:
    affected = service.delete_line(session, line_id)
    return {"deleted": str(line_id), "products_reset": affected}
