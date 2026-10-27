"""slim product_events: price moves to products as free text, drop video binding

Revision ID: 0012_slim_events
Revises: 0011_product_state_view
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_slim_events"
down_revision = "0011_product_state_view"
branch_labels = None
depends_on = None

NEW_VIEW = """
CREATE VIEW product_state AS
SELECT
    p.id AS product_id,
    COALESCE(latest.kind, 'unknown') AS status,
    announced.announced_on,
    released.released_on,
    latest.event_date AS last_event_on
FROM products p
LEFT JOIN LATERAL (
    SELECT e.kind, e.event_date
    FROM product_events e
    WHERE e.product_id = p.id
    ORDER BY e.event_date DESC, e.created_at DESC
    LIMIT 1
) latest ON true
LEFT JOIN LATERAL (
    SELECT min(e.event_date) AS announced_on
    FROM product_events e
    WHERE e.product_id = p.id AND e.kind = 'announced'
) announced ON true
LEFT JOIN LATERAL (
    SELECT min(e.event_date) AS released_on
    FROM product_events e
    WHERE e.product_id = p.id AND e.kind = 'released'
) released ON true
"""

OLD_VIEW = """
CREATE VIEW product_state AS
SELECT
    p.id AS product_id,
    COALESCE(latest.kind, 'unknown') AS status,
    priced.price,
    COALESCE(priced.price_currency, 'CNY') AS price_currency,
    announced.announced_on,
    released.released_on,
    latest.event_date AS last_event_on
FROM products p
LEFT JOIN LATERAL (
    SELECT e.kind, e.event_date
    FROM product_events e
    WHERE e.product_id = p.id
    ORDER BY e.event_date DESC, e.created_at DESC
    LIMIT 1
) latest ON true
LEFT JOIN LATERAL (
    SELECT e.price, e.price_currency
    FROM product_events e
    WHERE e.product_id = p.id AND e.price IS NOT NULL
    ORDER BY e.event_date DESC, e.created_at DESC
    LIMIT 1
) priced ON true
LEFT JOIN LATERAL (
    SELECT min(e.event_date) AS announced_on
    FROM product_events e
    WHERE e.product_id = p.id AND e.kind = 'announced'
) announced ON true
LEFT JOIN LATERAL (
    SELECT min(e.event_date) AS released_on
    FROM product_events e
    WHERE e.product_id = p.id AND e.kind = 'released'
) released ON true
"""


def upgrade() -> None:
    op.add_column("products", sa.Column("price", sa.String(64), nullable=True))
    op.execute("""
        UPDATE products p
        SET price = latest.price_text
        FROM (
            SELECT DISTINCT ON (product_id) product_id, price_text
            FROM product_events
            WHERE price_text IS NOT NULL AND price_text <> ''
            ORDER BY product_id, event_date DESC, created_at DESC
        ) latest
        WHERE latest.product_id = p.id
    """)

    op.execute("DROP VIEW product_state")
    op.drop_constraint("uq_product_events_source", "product_events", type_="unique")
    op.drop_column("product_events", "price")
    op.drop_column("product_events", "price_currency")
    op.drop_column("product_events", "price_text")
    op.drop_column("product_events", "video_id")
    op.drop_column("product_events", "video_time_seconds")
    op.drop_column("product_events", "note")
    op.create_unique_constraint(
        "uq_product_events_slot", "product_events", ["product_id", "event_date", "kind"]
    )
    op.execute(NEW_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW product_state")
    op.drop_constraint("uq_product_events_slot", "product_events", type_="unique")
    op.add_column("product_events", sa.Column("price", sa.Numeric(12, 2)))
    op.add_column("product_events", sa.Column("price_currency", sa.String(3), nullable=False, server_default="CNY"))
    op.add_column("product_events", sa.Column("price_text", sa.String(64)))
    op.add_column("product_events", sa.Column("video_id", sa.String(32)))
    op.add_column("product_events", sa.Column("video_time_seconds", sa.Integer()))
    op.add_column("product_events", sa.Column("note", sa.Text()))
    op.create_unique_constraint(
        "uq_product_events_source", "product_events", ["product_id", "video_id", "event_date"]
    )
    op.execute(OLD_VIEW)
    op.drop_column("products", "price")
