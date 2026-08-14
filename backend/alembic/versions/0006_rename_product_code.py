"""rename manufacturer_code to product_code
Revision ID: 0006_rename_product_code
Revises: 0005_restore_manufacturer_code
Create Date: 2026-08-14
"""
from alembic import op

revision = "0006_rename_product_code"
down_revision = "0005_restore_manufacturer_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("products", "manufacturer_code", new_column_name="product_code")


def downgrade() -> None:
    op.alter_column("products", "product_code", new_column_name="manufacturer_code")
