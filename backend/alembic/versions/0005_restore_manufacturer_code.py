"""restore manufacturer product code
Revision ID: 0005_restore_manufacturer_code
Revises: 0004_simplify_product_fields
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_restore_manufacturer_code"
down_revision = "0004_simplify_product_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("manufacturer_code", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "manufacturer_code")
