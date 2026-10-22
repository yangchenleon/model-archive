import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, or_, func
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    res = session.scalars(select(Product).where(
        or_(
            Product.manufacturer.ilike("%万代%"),
            Product.manufacturer.ilike("%Bandai%"),
            Product.product_line == "RG",
            Product.product_code.ilike("RG%")
        )
    )).all()
    print(f"Total matching products: {len(res)}")
    for p in res[:20]:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line} | Origin: {p.origin_type} | Source: {p.source}")
        print(f"  Detail: {p.detail[:60] if p.detail else 'None'}")
