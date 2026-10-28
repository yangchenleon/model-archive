"""rename tags.attached_at to printed_at

The sticker's timestamp is driven by printing, not by a human "I stuck it on"
click: once a sheet comes out of the printer the label is treated as applied.
Printing is the only event we can observe, so the column says so.

Revision ID: 0016_tag_printed_at
Revises: 0015_assets_tags_audit
Create Date: 2026-10-27
"""
from alembic import op

revision = "0016_tag_printed_at"
down_revision = "0015_assets_tags_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("tags", "attached_at", new_column_name="printed_at")


def downgrade() -> None:
    op.alter_column("tags", "printed_at", new_column_name="attached_at")
