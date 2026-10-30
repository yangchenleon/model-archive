"""add edition/craft and tighten release channels

- edition: official version label, free text, not identity
- craft: single-value common finish/process enum, NULL = none/unknown
- release channels: regular / pb / base / event / lottery / limited; NULL unknown
- existing 'other' rows become NULL (the old catch-all is removed)

Revision ID: 0026_edition_craft
Revises: 0025_product_release_date
Create Date: 2026-10-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0026_edition_craft"
down_revision = "0025_product_release_date"
branch_labels = None
depends_on = None

CRAFTS = (
    "clear",
    "transparent",
    "plated",
    "clear_plated",
    "color_plated",
    "pearl",
    "metallic",
    "coating",
    "matte",
    "crystal",
    "luminous",
)


def upgrade() -> None:
    op.add_column("products", sa.Column("edition", sa.String(120), nullable=True))
    op.add_column("products", sa.Column("craft", sa.String(24), nullable=True))
    op.create_index("ix_products_edition", "products", ["edition"])
    op.create_index("ix_products_craft", "products", ["craft"])

    op.execute("UPDATE products SET release_channel = NULL WHERE release_channel = 'other'")
    op.drop_constraint("ck_products_release_channel", "products", type_="check")
    op.create_check_constraint(
        "ck_products_release_channel",
        "products",
        "release_channel IS NULL OR release_channel IN ('regular', 'pb', 'base', 'event', 'lottery', 'limited')",
    )
    values = ", ".join(f"'{value}'" for value in CRAFTS)
    op.create_check_constraint(
        "ck_products_craft",
        "products",
        f"craft IS NULL OR craft IN ({values})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_craft", "products", type_="check")
    op.drop_constraint("ck_products_release_channel", "products", type_="check")
    op.create_check_constraint(
        "ck_products_release_channel",
        "products",
        "release_channel IS NULL OR release_channel IN ('regular', 'pb', 'limited', 'event', 'other')",
    )
    op.drop_index("ix_products_craft", table_name="products")
    op.drop_index("ix_products_edition", table_name="products")
    op.drop_column("products", "craft")
    op.drop_column("products", "edition")
