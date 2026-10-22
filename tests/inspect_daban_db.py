import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, or_
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    codes = ["6660", "8835", "8839", "6629", "6658"]
    res = session.scalars(select(Product).where(
        or_(
            Product.manufacturer.ilike("%大班%"),
            Product.product_code.in_(codes)
        )
    )).all()
    
    print(f"Total found: {len(res)}")
    for p in res:
        if p.product_code in codes or "66" in (p.product_code or ""):
            print(f"ID: {p.id}")
            print(f"  Manufacturer: {p.manufacturer}")
            print(f"  Code: {p.product_code}")
            print(f"  Line: {p.product_line}")
            print(f"  Origin Type: {p.origin_type}")
            print(f"  Kit Name: {p.kit_name}")
            print(f"  Source: {p.source}")
            print(f"  Detail: {p.detail[:100] if p.detail else 'None'}")
            print("-" * 40)
