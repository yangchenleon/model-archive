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
    names = ["格雷斯", "高文", "阿基里斯", "兰斯洛特", "加拉哈德", "贝狄威尔", "特里斯坦", "帕西瓦尔", "马尔洛克", "圆桌骑士"]
    res = session.scalars(select(Product).where(
        or_(*[Product.kit_name.ilike(f"%{n}%") for n in names], *[Product.product_line.ilike(f"%{n}%") for n in names])
    )).all()
    print(f"Found {len(res)} matches in DB:")
    for p in res:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | Line: {p.product_line} | Origin: {p.origin_type}")
        print(f"  Detail: {p.detail[:60] if p.detail else 'None'}")
