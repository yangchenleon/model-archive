"""one photo per asset, first version: object storage behind an S3 key

The row is metadata only; the bytes live in the object store (S3 API) so the
database stays a backup-able text artifact and images can grow without turning
`pg_dump` into a 50 GB operation. `object_key` is the content hash, so the same
photo uploaded twice (or shared by two assets) is stored once.

Selling or deleting an asset cascades the rows away; the objects are cleaned up
by the service, which knows when the last reference is gone.

Revision ID: 0031_asset_photos
Revises: 0030_trim_asset_fields
Create Date: 2026-11-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0031_asset_photos"
down_revision = "0030_trim_asset_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_photos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Uuid(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(200), nullable=False),
        sa.Column("thumb_key", sa.String(200), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "object_key", name="uq_asset_photos_asset_object"),
    )
    op.create_index("ix_asset_photos_asset_id", "asset_photos", ["asset_id"])
    op.create_index("ix_asset_photos_object_key", "asset_photos", ["object_key"])


def downgrade() -> None:
    op.drop_table("asset_photos")
