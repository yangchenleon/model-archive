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
    mfgs = ["聚匠", "KK"]
    res = session.scalars(select(Product).where(
        or_(*[Product.manufacturer.ilike(f"%{m}%") for m in mfgs])
    )).all()
    print(f"Total matching existing products: {len(res)}")
    for p in res:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line} | Origin: {p.origin_type}")
        print(f"  Detail: {p.detail[:60] if p.detail else 'None'}")

    # Also search for names like 猫耳00Q, 月高达, 驭灵
    keywords = ["猫耳", "月高达", "巴尔基尔", "驭灵", "陆战"]
    res_kw = session.scalars(select(Product).where(
        or_(*[Product.kit_name.ilike(f"%{k}%") for k in keywords])
    )).all()
    print(f"\nTotal matching keywords in DB: {len(res_kw)}")
    for p in res_kw[:15]:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line}")
