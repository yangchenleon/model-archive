"""trim assets: drop the five columns that never held a value

`rating`, `review`, `built_on`, `sold_on` and `sold_price` were added for a
"buy → build → review → sell" life cycle that the UI offered but nobody ever
filled: 779 rows, zero values in all five. They are removed instead of kept as
dead columns, because an input box that is never used is a lie about what the
system tracks.

- 已拼 is expressed by `state` (`displayed` / `stored`), so `built_on` is gone
  and collection progress now has a single source of truth.
- Sold time already lives in `asset_state_changes.changed_at`.
- A build review is a conversation with an agent (multi-field, multi-turn), so
  it belongs in its own `asset_reviews` table when that feature lands, not in
  nullable columns on every asset.

All five columns are empty, so the downgrade restores the schema without a
backfill.

Revision ID: 0030_trim_asset_fields
Revises: 0029_simplify_collections
Create Date: 2026-11-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0030_trim_asset_fields"
down_revision = "0029_simplify_collections"
branch_labels = None
depends_on = None

DROPPED = ("built_on", "rating", "review", "sold_on", "sold_price")


def upgrade() -> None:
    op.drop_constraint("ck_assets_rating", "assets", type_="check")
    for column in DROPPED:
        op.drop_column("assets", column)


def downgrade() -> None:
    op.add_column("assets", sa.Column("built_on", sa.Date()))
    op.add_column("assets", sa.Column("rating", sa.SmallInteger()))
    op.add_column("assets", sa.Column("review", sa.Text()))
    op.add_column("assets", sa.Column("sold_on", sa.Date()))
    op.add_column("assets", sa.Column("sold_price", sa.Numeric(12, 2)))
    op.create_check_constraint(
        "ck_assets_rating", "assets", "rating IS NULL OR rating BETWEEN 1 AND 5"
    )
