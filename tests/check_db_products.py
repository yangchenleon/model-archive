import os
import sys
from pathlib import Path

# If not running in docker, connect to mapped localhost port 15432
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import Product

with SessionLocal() as session:
    total = session.scalar(select(func.count(Product.id)))
    print(f"Total products in DB: {total}")
    
    # Check distinct origin_type
    origin_types = session.execute(select(Product.origin_type, func.count(Product.id)).group_by(Product.origin_type)).all()
    print("\nOrigin types in DB:")
    for ot, cnt in origin_types:
        print(f"  {ot}: {cnt}")
        
    # Check 星动 in DB
    xingdong_products = session.scalars(select(Product).where(Product.manufacturer == "星动")).all()
    print(f"\nExisting '星动' products in DB: {len(xingdong_products)}")
    for p in xingdong_products:
        print(f"  id={p.id} | mfg={p.manufacturer} | code={p.product_code} | line={p.product_line} | name={p.kit_name} | origin={p.origin_type} | src={p.source}")
