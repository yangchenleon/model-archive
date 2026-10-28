"""stamp audit rows at insert time, not at transaction start

``now()`` is frozen for the whole transaction, so two transitions recorded in one
transaction share a timestamp and the timeline order falls back to a random
UUID. ``clock_timestamp()`` advances per statement, which is what an append-only
audit wants.

Revision ID: 0018_audit_clock
Revises: 0017_tag_title
Create Date: 2026-10-28
"""
from alembic import op

revision = "0018_audit_clock"
down_revision = "0017_tag_title"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE asset_state_changes ALTER COLUMN changed_at SET DEFAULT clock_timestamp()")


def downgrade() -> None:
    op.execute("ALTER TABLE asset_state_changes ALTER COLUMN changed_at SET DEFAULT now()")
