"""drop the lottery release channel

Lottery / Ichiban Kuji is not a stable channel; those products are ordinary
limited releases whose lottery nature belongs in `edition`.

- existing lottery rows move to `limited`, with `一番赏` appended to `edition`
- the CHECK constraint no longer allows 'lottery'

Revision ID: 0028_drop_lottery
Revises: 0027_appearance_aliases
Create Date: 2026-11-04
"""
from __future__ import annotations

from alembic import op

revision = "0028_drop_lottery"
down_revision = "0027_appearance_aliases"
branch_labels = None
depends_on = None

OLD = "('regular', 'pb', 'base', 'event', 'lottery', 'limited')"
NEW = "('regular', 'pb', 'base', 'event', 'limited')"


def upgrade() -> None:
    op.execute("""
        UPDATE products
        SET release_channel = 'limited',
            edition = CASE
                WHEN edition IS NULL OR edition = '' THEN '一番赏'
                WHEN edition LIKE '%一番赏%' THEN edition
                ELSE edition || ';一番赏'
            END
        WHERE release_channel = 'lottery'
    """)
    op.drop_constraint("ck_products_release_channel", "products", type_="check")
    op.create_check_constraint(
        "ck_products_release_channel",
        "products",
        f"release_channel IS NULL OR release_channel IN {NEW}",
    )


def downgrade() -> None:
    op.drop_constraint("ck_products_release_channel", "products", type_="check")
    op.create_check_constraint(
        "ck_products_release_channel",
        "products",
        f"release_channel IS NULL OR release_channel IN {OLD}",
    )
    op.execute("""
        UPDATE products
        SET release_channel = 'lottery',
            edition = NULLIF(replace(coalesce(edition, ''), ';一番赏', ''), '')
        WHERE release_channel = 'limited' AND edition LIKE '%一番赏%'
    """)
