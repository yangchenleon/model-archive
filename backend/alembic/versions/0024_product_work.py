"""add products.work

Work / IP is an orthogonal, optional attribute (EVA, 勇者王, 机动警察, SEED,
UC...). It is not a product line and does not participate in product identity.
NULL means unknown; no backfill.

Revision ID: 0024_product_work
Revises: 0023_product_release_channel
Create Date: 2026-10-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0024_product_work"
down_revision = "0023_product_release_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("work", sa.String(120), nullable=True))
    op.create_index("ix_products_work", "products", ["work"])


def downgrade() -> None:
    op.drop_index("ix_products_work", table_name="products")
    op.drop_column("products", "work")
