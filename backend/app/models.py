from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("origin_type IN ('official', 'china_brand', 'ko', 'gk', 'third_party', 'unknown')", name="ck_products_origin_type"),
        CheckConstraint("confidence IN ('reported', 'verified', 'uncertain')", name="ck_products_confidence"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manufacturer: Mapped[str] = mapped_column(String(120))
    origin_type: Mapped[str] = mapped_column(String(32))
    product_line: Mapped[str | None] = mapped_column(String(120))
    scale: Mapped[str | None] = mapped_column(String(32))
    kit_name: Mapped[str] = mapped_column(String(240))
    variant_name: Mapped[str | None] = mapped_column(String(240))
    manufacturer_code: Mapped[str | None] = mapped_column(String(120))
    subject_name: Mapped[str | None] = mapped_column(String(240), index=True)
    box_art_key: Mapped[str | None] = mapped_column(String(240))
    detail: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16), default="reported")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assets: Mapped[list[Asset]] = relationship(back_populates="product")
class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("status IN ('wanted', 'ordered', 'owned_unbuilt', 'building', 'built', 'to_sell', 'to_trade', 'sold', 'returned', 'review')", name="ck_assets_status"),
        CheckConstraint("condition IN ('sealed', 'opened', 'complete', 'incomplete', 'unknown')", name="ck_assets_condition"),
        CheckConstraint("quantity > 0", name="ck_assets_quantity_positive"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), index=True)
    condition: Mapped[str] = mapped_column(String(32), default="unknown")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    storage_location: Mapped[str | None] = mapped_column(String(160))
    acquired_on: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    product: Mapped[Product] = relationship(back_populates="assets")
    events: Mapped[list[AssetEvent]] = relationship(back_populates="asset", cascade="all, delete-orphan")
class AssetEvent(Base):
    __tablename__ = "asset_events"
    __table_args__ = (CheckConstraint("event_type IN ('acquired', 'opened', 'build_started', 'build_completed', 'listed', 'traded', 'sold', 'returned', 'status_corrected', 'note')", name="ck_asset_events_type"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    detail: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    asset: Mapped[Asset] = relationship(back_populates="events")
