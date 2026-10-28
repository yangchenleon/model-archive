"""give tags a printable name, drop the role enum and the retired state

A tag is "one bag of one asset". Its name is what gets printed on the badge, so
it is free text with UI presets — the old body/extras/base enum could not say
"配件包 2".

``retired_at`` is gone: retiring a sticker is a physical fact nobody can
observe. Reprinting keeps the same row and code (it is the same bag); a second
bag is a new row with the next seq.

Revision ID: 0017_tag_title
Revises: 0016_tag_printed_at
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_tag_title"
down_revision = "0016_tag_printed_at"
branch_labels = None
depends_on = None

ROLE_TITLES = {"body": "本体", "extras": "余件", "base": "地台"}


def upgrade() -> None:
    op.add_column("tags", sa.Column("title", sa.String(24), nullable=False, server_default="本体"))
    for role, title in ROLE_TITLES.items():
        op.execute(f"UPDATE tags SET title = '{title}' WHERE role = '{role}'")
    op.drop_constraint("ck_tags_role", "tags", type_="check")
    op.drop_column("tags", "role")
    op.drop_column("tags", "retired_at")


def downgrade() -> None:
    op.add_column("tags", sa.Column("role", sa.String(16), nullable=False, server_default="body"))
    op.add_column("tags", sa.Column("retired_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE tags SET role = 'base' WHERE title = '地台'")
    op.execute("UPDATE tags SET role = 'extras' WHERE title <> '本体' AND title <> '地台'")
    op.create_check_constraint("ck_tags_role", "tags", "role IN ('body', 'extras', 'base')")
    op.drop_column("tags", "title")
