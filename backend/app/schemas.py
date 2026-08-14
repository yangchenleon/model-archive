from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
class ProductCreate(BaseModel):
    manufacturer: str | None = None
    product_code: str | None = None
    origin_type: str | None = None
    product_line: str | None = None
    kit_name: str
    variant_name: str | None = None
    detail: str | None = None
    source: str
class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
