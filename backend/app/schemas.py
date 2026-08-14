from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
class CatalogItemCreate(BaseModel):
    manufacturer: str
    origin_type: Literal["official", "china_brand", "ko", "gk", "third_party", "unknown"]
    product_line: str | None = None
    scale: str | None = None
    kit_name: str
    variant_name: str | None = None
    manufacturer_code: str | None = None
    subject_name: str | None = None
    box_art_key: str | None = None
    source_note: str | None = None
    confidence: Literal["reported", "verified", "uncertain"] = "reported"
class CatalogItemRead(CatalogItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
class AssetCreate(BaseModel):
    catalog_item_id: UUID
    status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"]
    condition: Literal["sealed", "opened", "complete", "incomplete", "unknown"] = "unknown"
    quantity: int = Field(default=1, ge=1)
    storage_location: str | None = None
    acquired_on: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    catalog_item_id: UUID
    status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"]
    condition: Literal["sealed", "opened", "complete", "incomplete", "unknown"]
    quantity: int
    storage_location: str | None
    acquired_on: date | None
    purchase_price: Decimal | None
    notes: str | None
    created_at: datetime
class AssetStatusUpdate(BaseModel):
    status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"]
    note: str | None = None
class CollectionTargetCreate(BaseModel):
    collection_name: str
    catalog_item_id: UUID
    decision: Literal["collect", "consider", "skip", "owned", "duplicate"]
    priority: int | None = Field(default=None, ge=1, le=5)
    reason: str | None = None
    rule_version: str | None = None
class CollectionTargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    collection_name: str
    catalog_item_id: UUID
    decision: Literal["collect", "consider", "skip", "owned", "duplicate"]
    priority: int | None
    reason: str | None
    rule_version: str | None
    created_at: datetime
class AssetEventCreate(BaseModel):
    asset_id: UUID
    event_type: Literal["acquired", "opened", "build_started", "build_completed", "listed", "traded", "sold", "returned", "status_corrected", "note"]
    occurred_at: datetime | None = None
    from_status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"] | None = None
    to_status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"] | None = None
    source_note: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
class AssetEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    event_type: Literal["acquired", "opened", "build_started", "build_completed", "listed", "traded", "sold", "returned", "status_corrected", "note"]
    occurred_at: datetime
    from_status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"] | None
    to_status: Literal["wanted", "ordered", "owned_unbuilt", "building", "built", "to_sell", "to_trade", "sold", "returned", "review"] | None
    source_note: str | None
    metadata_json: dict[str, Any]
