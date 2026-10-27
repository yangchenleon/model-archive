"""Flatten the extracted product timeline into the review queue.

Each mention in ``outputs/products/products.json`` becomes one ``review_items``
row: the reviewer either maps it onto an existing product, creates a new one, or
skips it. Re-running is idempotent (``source_key`` unique).

    .venv-tools/bin/python -m tools.seed_review_queue
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import date
from pathlib import Path

import psycopg


def parse_date(value: str) -> date:
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, default=Path("outputs/products/products.json"))
    parser.add_argument("--database-url", default=os.getenv(
        "DATABASE_URL", "postgresql://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"
    ))
    args = parser.parse_args()

    products = json.loads(args.products.read_text(encoding="utf-8"))
    rows = []
    for product in products:
        for entry in product["timeline"]:
            source_key = "|".join([
                entry.get("video_id") or "",
                str(entry.get("start") if entry.get("start") is not None else ""),
                entry["date"],
                product["brand"],
                product["model_name"],
            ])
            rows.append((
                uuid.uuid4(),
                source_key,
                parse_date(entry["date"]),
                entry.get("video_id"),
                int(entry["start"]) if entry.get("start") is not None else None,
                product["brand"],
                product["model_name"],
                product.get("line") or None,
                entry.get("variant") or None,
                entry.get("stage_cue") or None,
                entry.get("price") or None,
                entry.get("detail") or None,
                entry.get("evidence") or None,
            ))

    url = args.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from review_items")
        before = cur.fetchone()[0]
        cur.executemany(
            """
            insert into review_items
              (id, source_key, event_date, video_id, start_seconds, brand, product, line,
               variant, status_raw, price_raw, detail, evidence)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (source_key) do nothing
            """,
            rows,
        )
        conn.commit()
        cur.execute("select count(*) from review_items")
        after = cur.fetchone()[0]
    print(f"mentions {len(rows)} | review_items {before} -> {after} (+{after - before})")


if __name__ == "__main__":
    main()
