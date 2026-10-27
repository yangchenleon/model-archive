"""one event per (product, kind): upsert instead of append

Duplicate status events are collapsed to the newest one before the unique
constraint is tightened. The view additionally exposes event_count so the review
page can show whether a product already has timeline entries.

Revision ID: 0013_event_per_kind
Revises: 0012_slim_events
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_event_per_kind"
down_revision = "0012_slim_events"
branch_labels = None
depends_on = None

VIEW_SQL = """
CREATE VIEW product_state AS
SELECT
    p.id AS product_id,
    COALESCE(latest.kind, 'unknown') AS status,
    announced.announced_on,
    released.released_on,
    latest.event_date AS last_event_on,
    COALESCE(counts.event_count, 0) AS event_count
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
LEFT JOIN LATERAL (
    SELECT count(*) AS event_count
    FROM product_events e
    WHERE e.product_id = p.id
) counts ON true
"""

OLD_VIEW = """
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


def upgrade() -> None:
    # Keep only the newest event per (product, kind).
    op.execute("""
        DELETE FROM product_events e
        USING product_events newer
        WHERE e.product_id = newer.product_id
          AND e.kind = newer.kind
          AND (e.event_date, e.created_at) < (newer.event_date, newer.created_at)
    """)
    op.drop_constraint("uq_product_events_slot", "product_events", type_="unique")
    op.create_unique_constraint("uq_product_events_kind", "product_events", ["product_id", "kind"])
    op.execute("DROP VIEW product_state")
    op.execute(VIEW_SQL)


def downgrade() -> None:
    op.execute("DROP VIEW product_state")
    op.drop_constraint("uq_product_events_kind", "product_events", type_="unique")
    op.create_unique_constraint(
        "uq_product_events_slot", "product_events", ["product_id", "event_date", "kind"]
    )
    op.execute(OLD_VIEW)
