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
    res_88 = session.scalars(select(Product).where(Product.product_line == "88系列").order_by(Product.product_code)).all()
    print("88系列名称列表:")
    for p in res_88:
        print(f"  {p.product_code}: {p.kit_name}")

    res_eclipse = session.scalars(select(Product).where(Product.kit_name.like("%天蚀%"))).all()
    print("\n天蚀相关产品:")
    for p in res_eclipse:
        print(f"  {p.product_code}: {p.kit_name} ({p.manufacturer}, {p.product_line})")
