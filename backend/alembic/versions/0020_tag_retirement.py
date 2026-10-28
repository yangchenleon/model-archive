"""retire a sticker when its asset is sold

A sold kit's bags do not circulate any more, so the stickers stop being
printable and leave the working queues. The row is kept: it is still the
history of that physical bag, and deleting the asset would lose it.

Revision ID: 0020_tag_retirement
Revises: 0019_random_codes
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_tag_retirement"
down_revision = "0019_random_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tags", sa.Column("retired_at", sa.DateTime(timezone=True)))
    # Existing sold assets already have their stickers out of circulation; the
    # exact sale time is unknown, so stamp the migration as the retirement time.
    op.execute(
        """
        UPDATE tags
        SET retired_at = now()
        WHERE retired_at IS NULL
          AND asset_id IN (SELECT id FROM assets WHERE state = 'sold')
        """
    )


def downgrade() -> None:
    op.drop_column("tags", "retired_at")
