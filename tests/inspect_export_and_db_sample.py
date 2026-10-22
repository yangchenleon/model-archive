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
    sample = session.scalars(select(Product).limit(3)).all()
    print("DB Product objects:")
    for p in sample:
        print(f"  id: {p.id}")
        print(f"  manufacturer: {p.manufacturer}")
        print(f"  product_code: {p.product_code}")
        print(f"  origin_type:  {p.origin_type}")
        print(f"  product_line: {p.product_line}")
        print(f"  kit_name:     {p.kit_name}")
        print(f"  detail:       {p.detail[:30] if p.detail else None}...")
        print(f"  source:       {p.source}")
        print(f"  created_at:   {p.created_at}")
        print(f"  updated_at:   {p.updated_at}")
        print()
