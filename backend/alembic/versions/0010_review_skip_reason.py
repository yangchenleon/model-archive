"""review skip reason

Revision ID: 0010_review_skip_reason
Revises: 0009_product_events_review
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_review_skip_reason"
down_revision = "0009_product_events_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("review_items", sa.Column("skip_reason", sa.String(24), nullable=True))
    op.create_check_constraint(
        "ck_review_items_skip_reason",
        "review_items",
        "skip_reason IS NULL OR skip_reason IN ('later', 'ad', 'duplicate', 'invalid')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_review_items_skip_reason", "review_items", type_="check")
    op.drop_column("review_items", "skip_reason")
