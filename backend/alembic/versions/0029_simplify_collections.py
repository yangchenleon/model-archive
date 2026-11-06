"""simplify collections: drop status and the date columns

A collection is only a name plus a description plus its item list. "Completed"
is derived from the assets, so the intent status and the human dates were extra
state nobody needed.

Revision ID: 0029_simplify_collections
Revises: 0028_drop_lottery
Create Date: 2026-11-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0029_simplify_collections"
down_revision = "0028_drop_lottery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_collections_status", "collections", type_="check")
    op.drop_index("ix_collections_status", table_name="collections")
    op.drop_column("collections", "started_on")
    op.drop_column("collections", "target_on")
    op.drop_column("collections", "status")


def downgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
    )
    op.add_column("collections", sa.Column("started_on", sa.Date()))
    op.add_column("collections", sa.Column("target_on", sa.Date()))
    op.create_check_constraint(
        "ck_collections_status",
        "collections",
        "status IN ('planning', 'active', 'paused', 'abandoned')",
    )
    op.create_index("ix_collections_status", "collections", ["status"])
