from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from app.states import allowed_next_states


class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    product_code: Mapped[str | None] = mapped_column(String(120))
    product_line: Mapped[str | None] = mapped_column(String(120))
    kit_name: Mapped[str] = mapped_column(String(240))
    detail: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(160))
    price: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    assets: Mapped[list[Asset]] = relationship(back_populates="product")


class Collection(Base):
    """A human-defined set of catalog products. The items are the scope."""
    __tablename__ = "collections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planning', 'active', 'paused', 'abandoned')",
            name="ck_collections_status",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    started_on: Mapped[date | None] = mapped_column(Date)
    target_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list[CollectionItem]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionItem(Base):
    """One existing product in a collection. Nothing here is a placeholder."""
    __tablename__ = "collection_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "product_id", name="uq_collection_items_product"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    collection: Mapped[Collection] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint("state IN ('pending', 'mapped', 'created', 'skipped')", name="ck_review_items_state"),
        CheckConstraint(
            "skip_reason IS NULL OR skip_reason IN ('later', 'ad', 'duplicate', 'invalid')",
            name="ck_review_items_skip_reason",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(200), unique=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    video_id: Mapped[str | None] = mapped_column(String(32))
    start_seconds: Mapped[int | None] = mapped_column(Integer)
    brand: Mapped[str | None] = mapped_column(String(120))
    product: Mapped[str | None] = mapped_column(String(240))
    line: Mapped[str | None] = mapped_column(String(120))
    variant: Mapped[str | None] = mapped_column(String(120))
    status_raw: Mapped[str | None] = mapped_column(String(32))
    price_raw: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    skip_reason: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Asset(Base):
    """One owned kit. Its life is linear: bought once, built once, sold once."""

    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "state IN ('pending', 'keep', 'displayed', 'stored', 'sold')", name="ck_assets_state"
        ),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_assets_rating"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    # Six random characters (Crockford Base32); assigned by app.services.codes.
    code: Mapped[str] = mapped_column(String(20), unique=True)
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    acquired_on: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    built_on: Mapped[date | None] = mapped_column(Date)
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    review: Mapped[str | None] = mapped_column(Text)
    sold_on: Mapped[date | None] = mapped_column(Date)
    sold_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    product: Mapped[Product] = relationship(back_populates="assets")
    tags: Mapped[list[AssetTag]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    state_changes: Mapped[list[AssetStateChange]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    @property
    def allowed_next_states(self) -> list[str]:
        """Read-only view of the state machine, so the UI never invents a move."""
        return allowed_next_states(self.state)


class AssetTag(Base):
    """One physical sticker, i.e. one bag. Code derives from the asset code."""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("asset_id", "seq", name="uq_tags_asset_seq"),
        CheckConstraint("seq > 0", name="ck_tags_seq_positive"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(SmallInteger, default=1)
    code: Mapped[str] = mapped_column(String(24), unique=True)
    # What the badge prints: 本体 / 配件包 2 / 地台 ...
    title: Mapped[str] = mapped_column(String(24), default="本体")
    # Last time this sticker came out of the printer; a reprint just moves it.
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when the asset is sold. A retired sticker leaves the print queues and
    # cannot be reprinted, but the row stays as the history of the bag.
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    asset: Mapped[Asset] = relationship(back_populates="tags")


class AssetStateChange(Base):
    """Audit of state transitions: when the asset moved, not what it cost."""

    __tablename__ = "asset_state_changes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    from_state: Mapped[str | None] = mapped_column(String(16))
    to_state: Mapped[str] = mapped_column(String(16))
    # clock_timestamp(), not now(): an audit row is stamped when it is written,
    # so two transitions in one transaction keep their order.
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    note: Mapped[str | None] = mapped_column(Text)
    asset: Mapped[Asset] = relationship(back_populates="state_changes")
