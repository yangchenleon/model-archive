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
    mfgs = ["幻影模型", "雷恩模型", "钢铁模型"]
    for mfg in mfgs:
        items = session.scalars(select(Product).where(Product.manufacturer == mfg).order_by(Product.product_code)).all()
        print(f"=== {mfg} (共 {len(items)} 条) ===")
        for p in items:
            print(f"[{p.product_code}] {p.kit_name} | {p.product_line}")
            print(f"  详情: {p.detail}")
        print()
