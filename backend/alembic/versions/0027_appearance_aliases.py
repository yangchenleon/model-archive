"""rename craft to appearance, add aliases, switch appearance to Chinese labels

- `craft` becomes `appearance`: a scalable visual-effect label, free text, not identity.
  The old English enum values are translated to their Chinese labels so the column
  stays homogeneous; the CHECK constraint is dropped because the vocabulary is now
  edited by hand.
- `aliases` holds source names (78dm and similar), semicolon-separated. Re-syncing an
  external catalogue must look a product up by aliases, not by the display name,
  because display names are user-standardised.

Revision ID: 0027_appearance_aliases
Revises: 0026_edition_craft
Create Date: 2026-11-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0027_appearance_aliases"
down_revision = "0026_edition_craft"
branch_labels = None
depends_on = None

LABELS = {
    "clear": "彩透",
    "transparent": "透明",
    "plated": "电镀",
    "clear_plated": "透明电镀",
    "color_plated": "彩色电镀",
    "pearl": "珍珠",
    "metallic": "金属色",
    "coating": "特殊涂层",
    "matte": "消光",
    "crystal": "水晶",
    "luminous": "发光",
}


def upgrade() -> None:
    op.add_column("products", sa.Column("aliases", sa.Text(), nullable=True))
    op.drop_constraint("ck_products_craft", "products", type_="check")
    op.alter_column(
        "products",
        "craft",
        new_column_name="appearance",
        existing_type=sa.String(24),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "appearance",
        type_=sa.String(32),
        existing_type=sa.String(24),
        existing_nullable=True,
    )
    op.execute("ALTER INDEX ix_products_craft RENAME TO ix_products_appearance")
    for old, new in LABELS.items():
        op.execute(f"UPDATE products SET appearance = '{new}' WHERE appearance = '{old}'")


def downgrade() -> None:
    for old, new in LABELS.items():
        op.execute(f"UPDATE products SET appearance = '{old}' WHERE appearance = '{new}'")
    op.execute("ALTER INDEX ix_products_appearance RENAME TO ix_products_craft")
    op.alter_column(
        "products",
        "appearance",
        type_=sa.String(24),
        existing_type=sa.String(32),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "appearance",
        new_column_name="craft",
        existing_type=sa.String(24),
        existing_nullable=True,
    )
    values = ", ".join(f"'{value}'" for value in LABELS)
    op.create_check_constraint(
        "ck_products_craft",
        "products",
        f"craft IS NULL OR craft IN ({values})",
    )
    op.drop_column("products", "aliases")
