from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    manufacturer: str | None = None
    product_code: str | None = None
    product_line: str | None = None
    kit_name: str
    detail: str | None = None
    source: str
    price: str | None = None


class ProductUpdate(BaseModel):
    manufacturer: str | None = None
    product_code: str | None = None
    product_line: str | None = None
    kit_name: str | None = None
    detail: str | None = None
    source: str | None = None
    price: str | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    manufacturer: str | None = None
    product_code: str | None = None
    product_line: str | None = None
    kit_name: str
    detail: str | None = None
    source: str
    price: str | None = None
    created_at: datetime


class ReviewItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_key: str
    event_date: date
    video_id: str | None = None
    start_seconds: int | None = None
    brand: str | None = None
    product: str | None = None
    line: str | None = None
    variant: str | None = None
    status_raw: str | None = None
    price_raw: str | None = None
    detail: str | None = None
    evidence: str | None = None
    product_id: UUID | None = None
    state: str
    skip_reason: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class ReviewList(BaseModel):
    total: int
    items: list[ReviewItemRead]


class ReviewMapRequest(BaseModel):
    product_id: UUID


class ReviewSkipRequest(BaseModel):
    reason: str = "later"


class ReviewCreateRequest(BaseModel):
    manufacturer: str | None = None
    kit_name: str
    product_code: str | None = None
    product_line: str | None = None
    detail: str | None = None
    price_text: str | None = None
