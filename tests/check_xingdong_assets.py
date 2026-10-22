import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product, Asset

with SessionLocal() as session:
    stmt = select(Asset).join(Product).where(Product.manufacturer == "星动")
    assets = session.scalars(stmt).all()
    print(f"Total assets linked to 星动 products: {len(assets)}")
