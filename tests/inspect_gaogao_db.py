import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    # Check count of 高高
    count = session.scalar(select(func.count(Product.id)).where(Product.manufacturer == "高高"))
    print(f"Total 高高 products in DB: {count}")

    # Check distinct product lines for 高高
    lines = session.execute(
        select(Product.product_line, func.count(Product.id))
        .where(Product.manufacturer == "高高")
        .group_by(Product.product_line)
        .order_by(func.count(Product.id).desc())
    ).all()
    print("\n高高 product lines:")
    for pl, cnt in lines:
        print(f"  {pl}: {cnt}")

    # Check if 高高 already has MGSD or RG
    mgsd_rg = session.scalars(
        select(Product)
        .where(Product.manufacturer == "高高")
        .where(Product.product_line.in_(["MGSD", "RG", "HG"]))
    ).all()
    print(f"\nExisting 高高 in MGSD/RG/HG: {len(mgsd_rg)}")
    for p in mgsd_rg[:10]:
        print(f"  [{p.product_line}] [{p.product_code}] {p.kit_name} | origin={p.origin_type} | detail={p.detail}")
