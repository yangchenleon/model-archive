"""add products.updated_at
Revision ID: 0007_product_updated_at
Revises: 0006_rename_product_code
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa
revision = "0007_product_updated_at"
down_revision = "0006_rename_product_code"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.add_column("products", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
def downgrade() -> None:
    op.drop_column("products", "updated_at")
