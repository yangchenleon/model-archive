"""manufacturer and product-line taxonomy

Products stop carrying free-text manufacturer/product_line strings. The new
tables are:

- manufacturers: canonical name, 3-value category, tier 1..3, hidden sort
- product_lines: flat, owned by one manufacturer (HG != HGUC != HG GTO)

No alias table: a wrong name is data to fix, not something to paper over.
Unknown product lines stay NULL and are rendered as 未知.

Revision ID: 0022_manufacturer_taxonomy
Revises: 0021_collections
Create Date: 2026-10-28
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

revision = "0022_manufacturer_taxonomy"
down_revision = "0021_collections"
branch_labels = None
depends_on = None

CATEGORY_SEEDS = (
    ("万代", "gundam", 1),
    ("摩动核", "guomo", 1),
    ("和模线", "guomo", 1),
    ("长龙", "ko", 1),
    ("猛虎模型", "ko", 1),
)


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("category", sa.String(16)),
        sa.Column("tier", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "category IS NULL OR category IN ('gundam', 'guomo', 'ko')",
            name="ck_manufacturers_category",
        ),
        sa.CheckConstraint("tier BETWEEN 1 AND 3", name="ck_manufacturers_tier"),
    )
    op.create_index("ix_manufacturers_category", "manufacturers", ["category"])
    op.create_index("ix_manufacturers_tier", "manufacturers", ["tier"])

    op.create_table(
        "product_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "manufacturer_id",
            sa.Uuid(),
            sa.ForeignKey("manufacturers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("manufacturer_id", "name", name="uq_product_lines_manufacturer_name"),
    )
    op.create_index("ix_product_lines_manufacturer_id", "product_lines", ["manufacturer_id"])

    connection = op.get_bind()
    maker_names = connection.execute(sa.text(
        """
        SELECT DISTINCT btrim(manufacturer)
        FROM products
        WHERE manufacturer IS NOT NULL AND btrim(manufacturer) <> ''
        ORDER BY 1
        """
    )).scalars().all()

    maker_ids: dict[str, uuid.UUID] = {}
    for name in maker_names:
        maker_id = uuid.uuid4()
        maker_ids[name] = maker_id
        connection.execute(
            sa.text(
                """
                INSERT INTO manufacturers (id, name, category, tier, sort_order, created_at, updated_at)
                VALUES (:id, :name, NULL, 3, 0, now(), now())
                """
            ),
            {"id": maker_id, "name": name},
        )
    for name, category, tier in CATEGORY_SEEDS:
        connection.execute(
            sa.text(
                "UPDATE manufacturers SET category = :category, tier = :tier WHERE name = :name"
            ),
            {"category": category, "tier": tier, "name": name},
        )

    op.add_column("products", sa.Column("manufacturer_id", sa.Uuid(), nullable=True))
    op.add_column("products", sa.Column("product_line_id", sa.Uuid(), nullable=True))
    connection.execute(sa.text(
        """
        UPDATE products p
        SET manufacturer_id = m.id
        FROM manufacturers m
        WHERE btrim(p.manufacturer) = m.name
        """
    ))

    line_rows = connection.execute(sa.text(
        """
        SELECT DISTINCT btrim(manufacturer), btrim(product_line)
        FROM products
        WHERE manufacturer IS NOT NULL
          AND btrim(manufacturer) <> ''
          AND product_line IS NOT NULL
          AND btrim(product_line) <> ''
          AND btrim(product_line) <> '未知'
        ORDER BY 1, 2
        """
    )).all()
    for maker_name, line_name in line_rows:
        line_id = uuid.uuid4()
        connection.execute(
            sa.text(
                """
                INSERT INTO product_lines (id, manufacturer_id, name, sort_order, created_at, updated_at)
                VALUES (:id, :manufacturer_id, :name, 0, now(), now())
                """
            ),
            {"id": line_id, "manufacturer_id": maker_ids[maker_name], "name": line_name},
        )

    connection.execute(sa.text(
        """
        UPDATE products p
        SET product_line_id = l.id
        FROM product_lines l
        JOIN manufacturers m ON l.manufacturer_id = m.id
        WHERE p.manufacturer_id = m.id
          AND btrim(p.product_line) = l.name
        """
    ))

    op.add_column("review_items", sa.Column("manufacturer_id", sa.Uuid(), nullable=True))
    op.add_column("review_items", sa.Column("product_line_id", sa.Uuid(), nullable=True))
    connection.execute(sa.text(
        """
        UPDATE review_items r
        SET manufacturer_id = m.id
        FROM manufacturers m
        WHERE btrim(r.brand) = m.name
        """
    ))
    connection.execute(sa.text(
        """
        UPDATE review_items r
        SET product_line_id = l.id
        FROM product_lines l
        JOIN manufacturers m ON l.manufacturer_id = m.id
        WHERE r.manufacturer_id = m.id
          AND btrim(r.line) = l.name
        """
    ))

    op.alter_column("products", "manufacturer_id", nullable=False)
    op.create_foreign_key(
        "fk_products_manufacturer_id",
        "products",
        "manufacturers",
        ["manufacturer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_products_product_line_id",
        "products",
        "product_lines",
        ["product_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_products_manufacturer_id", "products", ["manufacturer_id"])
    op.create_index("ix_products_product_line_id", "products", ["product_line_id"])

    op.create_foreign_key(
        "fk_review_items_manufacturer_id",
        "review_items",
        "manufacturers",
        ["manufacturer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_review_items_product_line_id",
        "review_items",
        "product_lines",
        ["product_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_review_items_manufacturer_id", "review_items", ["manufacturer_id"])
    op.create_index("ix_review_items_product_line_id", "review_items", ["product_line_id"])

    op.drop_column("products", "manufacturer")
    op.drop_column("products", "product_line")


def downgrade() -> None:
    raise RuntimeError("0022_manufacturer_taxonomy is intentionally irreversible")
