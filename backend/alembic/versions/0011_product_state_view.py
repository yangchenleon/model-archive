"""derive product state from events, drop duplicated columns

products keeps only intrinsic identity; status / price / announced_on /
released_on are computed by the ``product_state`` view over product_events.
``origin_type`` was unused free text and ``updated_at`` duplicated what the event
stream already records, so both go.

Revision ID: 0011_product_state_view
Revises: 0010_review_skip_reason
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_product_state_view"
down_revision = "0010_review_skip_reason"
branch_labels = None
depends_on = None

VIEW_SQL = """
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
    op.execute(VIEW_SQL)
    op.drop_column("products", "origin_type")
    op.drop_column("products", "status")
    op.drop_column("products", "price")
    op.drop_column("products", "price_currency")
    op.drop_column("products", "announced_on")
    op.drop_column("products", "released_on")
    op.drop_column("products", "updated_at")


def downgrade() -> None:
    op.add_column("products", sa.Column("origin_type", sa.String(120)))
    op.add_column("products", sa.Column("status", sa.String(24), nullable=False, server_default="unknown"))
    op.add_column("products", sa.Column("price", sa.Numeric(12, 2)))
    op.add_column("products", sa.Column("price_currency", sa.String(3), nullable=False, server_default="CNY"))
    op.add_column("products", sa.Column("announced_on", sa.Date()))
    op.add_column("products", sa.Column("released_on", sa.Date()))
    op.add_column("products", sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.execute("""
        UPDATE products p
        SET status = s.status, price = s.price, price_currency = s.price_currency,
            announced_on = s.announced_on, released_on = s.released_on
        FROM product_state s
        WHERE s.product_id = p.id
    """)
    op.execute("DROP VIEW product_state")
