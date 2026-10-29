"""add products.release_channel

Channel is a closed, per-product attribute: regular / pb / limited / event /
other, with NULL meaning unknown. It is not part of product identity and is not
derived from 78dm's mixed series/grade categories.

Revision ID: 0023_product_release_channel
Revises: 0022_manufacturer_taxonomy
Create Date: 2026-10-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0023_product_release_channel"
down_revision = "0022_manufacturer_taxonomy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("release_channel", sa.String(16), nullable=True))
    op.create_check_constraint(
        "ck_products_release_channel",
        "products",
        "release_channel IS NULL OR release_channel IN ('regular', 'pb', 'limited', 'event', 'other')",
    )
    op.create_index("ix_products_release_channel", "products", ["release_channel"])


def downgrade() -> None:
    op.drop_index("ix_products_release_channel", table_name="products")
    op.drop_constraint("ck_products_release_channel", "products", type_="check")
    op.drop_column("products", "release_channel")
