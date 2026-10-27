"""drop product_events and the derived state view

The catalog only needs product identity + price. Review stays as an audit gate:
skip / map (link the mention to an existing product) / create (new product).
Mapping no longer changes the product.

Revision ID: 0014_drop_events
Revises: 0013_event_per_kind
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0014_drop_events"
down_revision = "0013_event_per_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS product_state")
    op.drop_column("review_items", "event_id")
    op.drop_table("product_events")


def downgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False, server_default="unknown"),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('announced', 'released', 'cancelled', 'unknown')", name="ck_product_events_kind"),
        sa.UniqueConstraint("product_id", "kind", name="uq_product_events_kind"),
    )
    op.create_index("ix_product_events_product_id", "product_events", ["product_id"])
    op.add_column("review_items", sa.Column("event_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("review_items_event_id_fkey", "review_items", "product_events", ["event_id"], ["id"], ondelete="SET NULL")
