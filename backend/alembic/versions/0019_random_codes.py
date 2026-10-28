"""random asset codes instead of the M-001 sequence

A sequential code tells the world how many kits you own and in what order you
bought them, and it looks like a database key. Six characters of Crockford
Base32 are just as short, survive a phone keypad, and carry no information.

Existing rows keep their code; the sequence and its default are dropped.

Revision ID: 0019_random_codes
Revises: 0018_audit_clock
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_random_codes"
down_revision = "0018_audit_clock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("assets", "code", server_default=None)
    op.execute("DROP SEQUENCE IF EXISTS asset_code_seq")


def downgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS asset_code_seq START 1")
    op.alter_column(
        "assets",
        "code",
        server_default=sa.text("'M-' || lpad(nextval('asset_code_seq')::text, 3, '0')"),
    )
