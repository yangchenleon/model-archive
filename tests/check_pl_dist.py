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
    res = session.execute(select(Product.manufacturer, Product.product_line, func.count(Product.id)).group_by(Product.manufacturer, Product.product_line)).all()
    print("Manufacturer & Product Line distribution:")
    for m, pl, cnt in res[:30]:
        print(f"  {m} | {pl} -> {cnt}")
