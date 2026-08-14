"""add foreign key indexes
Revision ID: 0002_foreign_key_indexes
Revises: 0001_initial_inventory
Create Date: 2026-08-14
"""
from alembic import op
revision = "0002_foreign_key_indexes"
down_revision = "0001_initial_inventory"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_index("ix_assets_catalog_item_id", "assets", ["catalog_item_id"])
    op.create_index("ix_collection_targets_catalog_item_id", "collection_targets", ["catalog_item_id"])
def downgrade() -> None:
    op.drop_index("ix_collection_targets_catalog_item_id", table_name="collection_targets")
    op.drop_index("ix_assets_catalog_item_id", table_name="assets")
