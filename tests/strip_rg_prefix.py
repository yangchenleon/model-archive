import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    items = session.scalars(
        select(Product).where(
            Product.manufacturer == "万代",
            Product.product_line == "RG"
        ).order_by(Product.product_code)
    ).all()

    updated = 0
    for p in items:
        if p.product_code and p.product_code.startswith("RG"):
            new_code = p.product_code[2:]
            print(f"Updating [{p.product_code}] -> [{new_code}] {p.kit_name}")
            p.product_code = new_code
            updated += 1

    session.commit()
    print(f"\nFinished updating {updated} items.")
