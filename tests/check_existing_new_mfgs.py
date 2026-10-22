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
    mfgs = ["幻影", "雷恩", "钢铁"]
    res = session.scalars(select(Product).where(
        or_(*[Product.manufacturer.ilike(f"%{m}%") for m in mfgs])
    )).all()
    print(f"Total matching existing products: {len(res)}")
    for p in res:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line} | Origin: {p.origin_type}")
        print(f"  Detail: {p.detail[:60] if p.detail else 'None'}")

    # Also check if any codes match like 2001, ZG, VN
    res_codes = session.scalars(select(Product).where(
        or_(
            Product.product_code.ilike("2001%"),
            Product.product_code.ilike("ZG%"),
            Product.product_code.ilike("VN%"),
            Product.product_code.ilike("G00%"),
            Product.product_code.ilike("Z001%")
        )
    )).all()
    print(f"\nTotal matching codes: {len(res_codes)}")
    for p in res_codes:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line}")
