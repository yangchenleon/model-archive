"""rename catalog to products and remove collection targets
Revision ID: 0003_product_directory_scope
Revises: 0002_foreign_key_indexes
Create Date: 2026-08-14
"""
from alembic import op
revision = "0003_product_directory_scope"
down_revision = "0002_foreign_key_indexes"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.drop_table("collection_targets")
    op.drop_index("ix_assets_catalog_item_id", table_name="assets")
    op.rename_table("catalog_items", "products")
    op.execute("ALTER INDEX ix_catalog_items_subject_name RENAME TO ix_products_subject_name")
    op.drop_constraint("catalog_items_catalog_key_key", "products", type_="unique")
    op.drop_column("products", "catalog_key")
    op.alter_column("products", "source_note", new_column_name="detail")
    op.execute("ALTER TABLE products RENAME CONSTRAINT ck_catalog_items_origin_type TO ck_products_origin_type")
    op.execute("ALTER TABLE products RENAME CONSTRAINT ck_catalog_items_confidence TO ck_products_confidence")
    op.drop_constraint("assets_catalog_item_id_fkey", "assets", type_="foreignkey")
    op.alter_column("assets", "catalog_item_id", new_column_name="product_id")
    op.create_foreign_key("assets_product_id_fkey", "assets", "products", ["product_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_assets_product_id", "assets", ["product_id"])
    op.drop_constraint("assets_asset_key_key", "assets", type_="unique")
    op.drop_column("assets", "asset_key")
    op.alter_column("assets", "notes", new_column_name="detail")
    op.alter_column("asset_events", "source_note", new_column_name="detail")
def downgrade() -> None:
    raise RuntimeError("0003_product_directory_scope is intentionally irreversible")
