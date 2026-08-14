"""simplify product directory fields
Revision ID: 0004_simplify_product_fields
Revises: 0003_product_directory_scope
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
revision = "0004_simplify_product_fields"
down_revision = "0003_product_directory_scope"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.drop_constraint("ck_products_origin_type", "products", type_="check")
    op.drop_constraint("ck_products_confidence", "products", type_="check")
    op.drop_index("ix_products_subject_name", table_name="products")
    op.alter_column("products", "manufacturer", existing_type=sa.String(120), nullable=True)
    op.alter_column("products", "origin_type", existing_type=sa.String(32), type_=sa.String(120), nullable=True)
    op.drop_column("products", "scale")
    op.drop_column("products", "manufacturer_code")
    op.drop_column("products", "subject_name")
    op.drop_column("products", "box_art_key")
    op.drop_column("products", "confidence")
    op.add_column("products", sa.Column("source", sa.String(160), nullable=False))
def downgrade() -> None:
    raise RuntimeError("0004_simplify_product_fields is intentionally irreversible")
