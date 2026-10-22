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
    items = session.scalars(
        select(Product).where(Product.manufacturer == "伊达斯科技").order_by(Product.kit_name)
    ).all()
    print(f"Total current items for 伊达斯科技: {len(items)}")
    for p in items:
        print(f"ID: {p.id} | Name: {p.kit_name}")
