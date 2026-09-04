"""drop product variant_name and merge into kit_name

Revision ID: 0008_drop_product_variant_name
Revises: 0007_product_updated_at
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_drop_product_variant_name"
down_revision = "0007_product_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE products
        SET kit_name = kit_name || '（' || trim(variant_name) || '）', updated_at = NOW()
        WHERE variant_name IS NOT NULL
          AND trim(variant_name) != ''
          AND variant_name NOT IN ('无', '未指定', '未知', '默认')
          AND position(trim(variant_name) in kit_name) = 0
    """))
    op.drop_column("products", "variant_name")


def downgrade() -> None:
    op.add_column("products", sa.Column("variant_name", sa.String(240), nullable=True))
