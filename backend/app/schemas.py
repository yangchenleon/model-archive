from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ManufacturerCreate(BaseModel):
    name: str
    category: str | None = None
    tier: int = Field(default=3, ge=1, le=3)
    sort_order: int = 0
    description: str | None = None


class ManufacturerUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    tier: int | None = Field(default=None, ge=1, le=3)
    sort_order: int | None = None
    description: str | None = None


class ManufacturerRead(BaseModel):
    id: UUID
    name: str
    category: str | None = None
    tier: int = 3
    sort_order: int = 0
    description: str | None = None
    product_count: int = 0
    line_count: int = 0
    created_at: datetime
    updated_at: datetime


class ManufacturerBrief(BaseModel):
    id: UUID
    name: str
    category: str | None = None
    tier: int = 3
    sort_order: int = 0


class ManufacturerMergeRequest(BaseModel):
    target_id: UUID


class ProductLineCreate(BaseModel):
    manufacturer_id: UUID
    name: str
    sort_order: int = 0


class ProductLineUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


class ProductLineRead(BaseModel):
    id: UUID
    manufacturer_id: UUID
    name: str
    sort_order: int = 0
    product_count: int = 0


class ProductCreate(BaseModel):
    manufacturer_id: UUID
    product_line_id: UUID | None = None
    product_code: str | None = None
    kit_name: str
    release_channel: str | None = None
    detail: str | None = None
    source: str
    price: str | None = None


class ProductUpdate(BaseModel):
    manufacturer_id: UUID | None = None
    product_line_id: UUID | None = None
    product_code: str | None = None
    kit_name: str | None = None
    release_channel: str | None = None
    detail: str | None = None
    source: str | None = None
    price: str | None = None


class ProductBulkChannel(BaseModel):
    product_ids: list[UUID]
    release_channel: str | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    manufacturer_id: UUID
    product_line_id: UUID | None = None
    manufacturer: str | None = None
    product_code: str | None = None
    product_line: str | None = None
    kit_name: str
    release_channel: str | None = None
    detail: str | None = None
    source: str
    price: str | None = None
    created_at: datetime


class CollectionCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "active"
    started_on: date | None = None
    target_on: date | None = None


class CollectionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    started_on: date | None = None
    target_on: date | None = None


class CollectionStats(BaseModel):
    total: int = 0
    owned: int = 0
    built: int = 0
    unbuilt: int = 0
    missing: int = 0
    sold_only: int = 0
    extra_copies: int = 0
    percent: float = 0
    completed: bool = False


class CollectionRead(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    status: str
    started_on: date | None = None
    target_on: date | None = None
    created_at: datetime
    updated_at: datetime
    stats: CollectionStats


class CollectionItemCreate(BaseModel):
    product_id: UUID


class CollectionItemUpdate(BaseModel):
    note: str | None = None


class CollectionItemRead(BaseModel):
    id: UUID
    product_id: UUID
    name: str
    manufacturer: str | None = None
    product_line: str | None = None
    product_code: str | None = None
    note: str | None = None
    owned: bool
    built: bool
    sold_only: bool
    asset_count: int = 0
    asset_states: list[str] = []
    sold_count: int = 0


class CollectionItemList(BaseModel):
    total: int
    items: list[CollectionItemRead]


class CollectionBulkAdd(BaseModel):
    product_ids: list[UUID]


class CollectionBulkAddResult(BaseModel):
    added: int
    skipped: int


class CollectionBulkRemove(BaseModel):
    item_ids: list[UUID]


class CollectionBulkRemoveResult(BaseModel):
    removed: int


class ProductCollectionRead(BaseModel):
    id: UUID
    title: str
    owned: bool


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
    manufacturer_id: UUID | None = None
    product_line_id: UUID | None = None
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
    manufacturer_id: UUID
    product_line_id: UUID | None = None
    kit_name: str
    release_channel: str | None = None
    product_code: str | None = None
    detail: str | None = None
    price_text: str | None = None


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kit_name: str
    manufacturer_id: UUID
    product_line_id: UUID | None = None
    manufacturer: str | None = None
    product_line: str | None = None
    release_channel: str | None = None


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    seq: int
    code: str
    title: str
    printed_at: datetime | None = None
    retired_at: datetime | None = None


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
    # Derived from app.states; the drawer and the bulk bar both read this so
    # the two surfaces cannot disagree about what is allowed.
    allowed_next_states: list[str] = []
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
    retired_at: datetime | None = None
