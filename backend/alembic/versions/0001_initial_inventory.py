"""initial inventory tables
Revision ID: 0001_initial_inventory
Revises:
Create Date: 2026-08-14
"""
from alembic import op
import sqlalchemy as sa
revision = "0001_initial_inventory"
down_revision = None
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("catalog_items", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("catalog_key", sa.String(160), nullable=False, unique=True), sa.Column("manufacturer", sa.String(120), nullable=False), sa.Column("origin_type", sa.String(32), nullable=False), sa.Column("product_line", sa.String(120)), sa.Column("scale", sa.String(32)), sa.Column("kit_name", sa.String(240), nullable=False), sa.Column("variant_name", sa.String(240)), sa.Column("manufacturer_code", sa.String(120)), sa.Column("subject_name", sa.String(240)), sa.Column("box_art_key", sa.String(240)), sa.Column("source_note", sa.Text()), sa.Column("confidence", sa.String(16), nullable=False, server_default="reported"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.CheckConstraint("origin_type IN ('official', 'china_brand', 'ko', 'gk', 'third_party', 'unknown')", name="ck_catalog_items_origin_type"), sa.CheckConstraint("confidence IN ('reported', 'verified', 'uncertain')", name="ck_catalog_items_confidence"))
    op.create_index("ix_catalog_items_subject_name", "catalog_items", ["subject_name"])
    op.create_table("assets", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("asset_key", sa.String(160), nullable=False, unique=True), sa.Column("catalog_item_id", sa.Uuid(), sa.ForeignKey("catalog_items.id", ondelete="RESTRICT"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("condition", sa.String(32), nullable=False, server_default="unknown"), sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"), sa.Column("storage_location", sa.String(160)), sa.Column("acquired_on", sa.Date()), sa.Column("purchase_price", sa.Numeric(12, 2)), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.CheckConstraint("status IN ('wanted', 'ordered', 'owned_unbuilt', 'building', 'built', 'to_sell', 'to_trade', 'sold', 'returned', 'review')", name="ck_assets_status"), sa.CheckConstraint("condition IN ('sealed', 'opened', 'complete', 'incomplete', 'unknown')", name="ck_assets_condition"), sa.CheckConstraint("quantity > 0", name="ck_assets_quantity_positive"))
    op.create_index("ix_assets_status", "assets", ["status"])
    op.create_table("collection_targets", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("collection_name", sa.String(160), nullable=False), sa.Column("catalog_item_id", sa.Uuid(), sa.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False), sa.Column("decision", sa.String(16), nullable=False), sa.Column("priority", sa.SmallInteger()), sa.Column("reason", sa.Text()), sa.Column("rule_version", sa.String(80)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("collection_name", "catalog_item_id", name="uq_collection_target"), sa.CheckConstraint("decision IN ('collect', 'consider', 'skip', 'owned', 'duplicate')", name="ck_collection_targets_decision"), sa.CheckConstraint("priority IS NULL OR priority BETWEEN 1 AND 5", name="ck_collection_targets_priority"))
    op.create_index("ix_collection_targets_name", "collection_targets", ["collection_name"])
    op.create_table("asset_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False), sa.Column("event_type", sa.String(32), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("from_status", sa.String(32)), sa.Column("to_status", sa.String(32)), sa.Column("source_note", sa.Text()), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")), sa.CheckConstraint("event_type IN ('acquired', 'opened', 'build_started', 'build_completed', 'listed', 'traded', 'sold', 'returned', 'status_corrected', 'note')", name="ck_asset_events_type"))
    op.create_index("ix_asset_events_asset_occurred", "asset_events", ["asset_id", "occurred_at"])
def downgrade() -> None:
    op.drop_table("asset_events")
    op.drop_table("collection_targets")
    op.drop_table("assets")
    op.drop_table("catalog_items")
