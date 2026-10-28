from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


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


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kit_name: str
    manufacturer: str | None = None
    product_line: str | None = None


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    seq: int
    code: str
    title: str
    printed_at: datetime | None = None


class TagCreate(BaseModel):
    title: str = "本体"


class TagUpdate(BaseModel):
    title: str


class AssetStateChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    from_state: str | None = None
    to_state: str
    changed_at: datetime
    note: str | None = None


class AssetCreate(BaseModel):
    product_id: UUID
    state: str = "pending"
    acquired_on: date | None = None
    purchase_price: Decimal | None = None
    note: str | None = None


class AssetUpdate(BaseModel):
    state: str | None = None
    acquired_on: date | None = None
    purchase_price: Decimal | None = None
    built_on: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    review: str | None = None
    sold_on: date | None = None
    sold_price: Decimal | None = None
    note: str | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    state: str
    note: str | None = None
    acquired_on: date | None = None
    purchase_price: Decimal | None = None
    built_on: date | None = None
    rating: int | None = None
    review: str | None = None
    sold_on: date | None = None
    sold_price: Decimal | None = None
    created_at: datetime
    product: ProductBrief | None = None
    tags: list[TagRead] = []


class BulkAssetCreate(BaseModel):
    product_ids: list[UUID]
    state: str = "pending"
    acquired_on: date | None = None


class BulkStateUpdate(BaseModel):
    asset_ids: list[UUID]
    state: str
    note: str | None = None


class BulkTagCreate(BaseModel):
    asset_ids: list[UUID]
    title: str = "本体"


class BulkTagPrint(BaseModel):
    tag_ids: list[UUID]


class TagQueueItem(BaseModel):
    id: UUID
    code: str
    seq: int
    title: str
    asset_id: UUID
    asset_code: str
    kit_name: str
    manufacturer: str | None = None
    product_line: str | None = None
    created_at: datetime
    printed_at: datetime | None = None
