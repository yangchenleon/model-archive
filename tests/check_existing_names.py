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
    keywords = ["扎古", "厄运", "金恩", "铁球", "钢坦克"]
    res = session.scalars(select(Product).where(
        or_(*[Product.kit_name.ilike(f"%{k}%") for k in keywords])
    )).all()
    print(f"Total matching products: {len(res)}")
    for p in res[:35]:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | {p.product_line}")
