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
    codes = ["6660", "8835", "8839"]
    res = session.scalars(select(Product).where(Product.product_code.in_(codes)).order_by(Product.product_code)).all()
    print(f"Verified count: {len(res)}")
    for p in res:
        print(f"ID: {p.id}")
        print(f"  Manufacturer: {p.manufacturer}")
        print(f"  Product Code: {p.product_code}")
        print(f"  Product Line: {p.product_line}")
        print(f"  Kit Name: {p.kit_name}")
        print(f"  Origin Type: {p.origin_type}")
        print(f"  Source: {p.source}")
        print(f"  Detail: {p.detail}")
        print(f"  Created At: {p.created_at}")
        print("-" * 60)
