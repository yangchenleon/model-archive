"""rebuild assets around build state, add tags and a state audit log

``assets`` was a box-inventory sketch: quantity, storage_location, and a
wanted/ordered/to_sell/to_trade status list. It is replaced by one row per owned
kit, carrying the facts that happen once in its life (bought, built, sold) plus
the review. Stickers become ``tags`` — one physical bag each — and state
transitions are audited in ``asset_state_changes``.

The previous shape mixed per-kind attributes into a single event stream
(rating on an "acquired" row, amount on a "noted" row). Every field here is
nullable but has exactly one meaning.

All three tables are empty, so this rebuild drops instead of migrating rows.

Revision ID: 0015_assets_tags_audit
Revises: 0014_drop_events
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_assets_tags_audit"
down_revision = "0014_drop_events"
branch_labels = None
depends_on = None

STATES = ("pending", "keep", "displayed", "stored", "sold")
ROLES = ("body", "extras", "base")


def upgrade() -> None:
    op.drop_table("asset_events")
    op.drop_table("assets")

    # Codes are allocated by the database, so a row inserted from psql still gets
    # a unique sticker number. Never reused: a deleted asset leaves its number dead.
    op.execute("CREATE SEQUENCE asset_code_seq START 1")

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(20),
            nullable=False,
            unique=True,
            server_default=sa.text("'M-' || lpad(nextval('asset_code_seq')::text, 3, '0')"),
        ),
        sa.Column("state", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text()),
        # 买入
        sa.Column("acquired_on", sa.Date()),
        sa.Column("purchase_price", sa.Numeric(12, 2)),
        # 拼装与评价
        sa.Column("built_on", sa.Date()),
        sa.Column("rating", sa.SmallInteger()),
        sa.Column("review", sa.Text()),
        # 卖出
        sa.Column("sold_on", sa.Date()),
        sa.Column("sold_price", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "state IN ('pending', 'keep', 'displayed', 'stored', 'sold')", name="ck_assets_state"
        ),
        sa.CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_assets_rating"),
    )
    op.create_index("ix_assets_product_id", "assets", ["product_id"])
    op.create_index("ix_assets_state", "assets", ["state"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("code", sa.String(24), nullable=False, unique=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="body"),
        sa.Column("attached_at", sa.DateTime(timezone=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "seq", name="uq_tags_asset_seq"),
        sa.CheckConstraint("seq > 0", name="ck_tags_seq_positive"),
        sa.CheckConstraint("role IN ('body', 'extras', 'base')", name="ck_tags_role"),
    )
    op.create_index("ix_tags_asset_id", "tags", ["asset_id"])

    op.create_table(
        "asset_state_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_state", sa.String(16)),
        sa.Column("to_state", sa.String(16), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("note", sa.Text()),
    )
    op.create_index("ix_asset_state_changes_asset", "asset_state_changes", ["asset_id", "changed_at"])


def downgrade() -> None:
    op.drop_table("asset_state_changes")
    op.drop_table("tags")
    op.drop_table("assets")
    op.execute("DROP SEQUENCE asset_code_seq")
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("storage_location", sa.String(160)),
        sa.Column("acquired_on", sa.Date()),
        sa.Column("purchase_price", sa.Numeric(12, 2)),
        sa.Column("detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('wanted', 'ordered', 'owned_unbuilt', 'building', 'built', "
            "'to_sell', 'to_trade', 'sold', 'returned', 'review')",
            name="ck_assets_status",
        ),
        sa.CheckConstraint(
            "condition IN ('sealed', 'opened', 'complete', 'incomplete', 'unknown')",
            name="ck_assets_condition",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_assets_quantity_positive"),
    )
    op.create_index("ix_assets_status", "assets", ["status"])
    op.create_table(
        "asset_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column("detail", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
    )
    op.create_index("ix_asset_events_asset_occurred", "asset_events", ["asset_id", "occurred_at"])
