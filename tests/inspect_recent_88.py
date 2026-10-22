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
    res = session.scalars(select(Product).where(Product.product_code.in_(["8831", "8832", "8833", "8836"]))).all()
    for p in res:
        print(f"[{p.product_code}] {p.kit_name}")
        print(f"  Manufacturer: {p.manufacturer}")
        print(f"  Line: {p.product_line}")
        print(f"  Origin: {p.origin_type}")
        print(f"  Source: {p.source}")
        print(f"  Detail: {p.detail}")
        print("-" * 50)
