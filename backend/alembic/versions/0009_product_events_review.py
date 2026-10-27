"""product lifecycle events and the review queue

Revision ID: 0009_product_events_review
Revises: 0008_drop_product_variant_name
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009_product_events_review"
down_revision = "0008_drop_product_variant_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("status", sa.String(24), nullable=False, server_default="unknown"))
    op.add_column("products", sa.Column("price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("price_currency", sa.String(3), nullable=False, server_default="CNY"))
    op.add_column("products", sa.Column("announced_on", sa.Date(), nullable=True))
    op.add_column("products", sa.Column("released_on", sa.Date(), nullable=True))

    op.create_table(
        "product_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default="unknown"),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("price_text", sa.String(64), nullable=True),
        sa.Column("video_id", sa.String(32), nullable=True),
        sa.Column("video_time_seconds", sa.Integer(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('announced', 'released', 'cancelled', 'unknown')", name="ck_product_events_kind"),
        sa.UniqueConstraint("product_id", "video_id", "event_date", name="uq_product_events_source"),
    )
    op.create_index("ix_product_events_product_id", "product_events", ["product_id"])

    op.create_table(
        "review_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_key", sa.String(200), nullable=False, unique=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("video_id", sa.String(32), nullable=True),
        sa.Column("start_seconds", sa.Integer(), nullable=True),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("product", sa.String(240), nullable=True),
        sa.Column("line", sa.String(120), nullable=True),
        sa.Column("variant", sa.String(120), nullable=True),
        sa.Column("status_raw", sa.String(32), nullable=True),
        sa.Column("price_raw", sa.String(64), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("product_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("state IN ('pending', 'mapped', 'created', 'skipped')", name="ck_review_items_state"),
    )
    op.create_index("ix_review_items_state", "review_items", ["state"])
    op.create_index("ix_review_items_event_date", "review_items", ["event_date"])


def downgrade() -> None:
    op.drop_table("review_items")
    op.drop_table("product_events")
    op.drop_column("products", "released_on")
    op.drop_column("products", "announced_on")
    op.drop_column("products", "price_currency")
    op.drop_column("products", "price")
    op.drop_column("products", "status")
