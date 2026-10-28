"""collections and their product targets

A collection is a human-defined list of products that already exist in the
catalog. There are no placeholder rows and no saved filters: the item table is
the scope. Progress is computed from ``assets`` on read and never stored.

Revision ID: 0021_collections
Revises: 0020_tag_retirement
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_collections"
down_revision = "0020_tag_retirement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("started_on", sa.Date()),
        sa.Column("target_on", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('planning', 'active', 'paused', 'abandoned')",
            name="ck_collections_status",
        ),
    )
    op.create_index("ix_collections_status", "collections", ["status"])

    op.create_table(
        "collection_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "collection_id",
            sa.Uuid(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("collection_id", "product_id", name="uq_collection_items_product"),
    )
    op.create_index("ix_collection_items_collection_id", "collection_items", ["collection_id"])
    op.create_index("ix_collection_items_product_id", "collection_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("collection_items")
    op.drop_table("collections")
