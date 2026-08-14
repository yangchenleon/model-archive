from __future__ import annotations
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict
class ProductCreate(BaseModel):
    manufacturer: str
    origin_type: Literal["official", "china_brand", "ko", "gk", "third_party", "unknown"]
    product_line: str | None = None
    scale: str | None = None
    kit_name: str
    variant_name: str | None = None
    manufacturer_code: str | None = None
    subject_name: str | None = None
    box_art_key: str | None = None
    detail: str | None = None
    confidence: Literal["reported", "verified", "uncertain"] = "reported"
class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
