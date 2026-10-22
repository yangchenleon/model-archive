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
    # 检查特定编号
    target_codes = ["6660", "8835", "8839", "6629", "6658", "8802", "8810", "8812", "8814", "8816", "8820", "8822"]
    res = session.scalars(select(Product).where(Product.product_code.in_(target_codes))).all()
    print(f"Target codes found ({len(res)}):")
    for p in res:
        print(f"  [{p.product_code}] {p.manufacturer} - {p.kit_name} (Line: {p.product_line}, Origin: {p.origin_type}, Source: {p.source})")
        print(f"    Detail: {p.detail}")
    
    # 查找所有以88开头的编号或者Line为88系列
    res_88 = session.scalars(select(Product).where(
        or_(
            Product.product_code.like("88%"),
            Product.product_line.ilike("%88%")
        )
    )).all()
    print(f"\nTotal 88 series products ({len(res_88)}):")
    for p in res_88[:10]:
        print(f"  [{p.product_code}] {p.manufacturer} - {p.kit_name} (Line: {p.product_line}, Origin: {p.origin_type}, Source: {p.source})")

    # 查找所有不同的 origin_type
    all_origin_types = session.execute(select(Product.origin_type).distinct()).all()
    print("\nDistinct origin_types in DB:")
    for ot in all_origin_types:
        print(" ", ot[0])

    # 查找所有不同的 source
    all_sources = session.execute(select(Product.source, Product.origin_type).distinct()).all()
    print("\nDistinct (source, origin_type) samples:")
    for s, ot in all_sources[:15]:
        print(f"  origin={ot} | source={s}")
