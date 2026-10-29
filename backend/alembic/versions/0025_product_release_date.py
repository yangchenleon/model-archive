"""add products.release_date

The product's release date is meaningful for display and sorting; created_at
stays internal only. Existing rows are NULL until backfilled from a source.

Revision ID: 0025_product_release_date
Revises: 0024_product_work
Create Date: 2026-10-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0025_product_release_date"
down_revision = "0024_product_work"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("release_date", sa.Date(), nullable=True))
    op.create_index("ix_products_release_date", "products", ["release_date"])


def downgrade() -> None:
    op.drop_index("ix_products_release_date", table_name="products")
    op.drop_column("products", "release_date")
