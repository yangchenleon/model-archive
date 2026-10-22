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
    mfgs = ["胶佬", "机核", "伊达斯", "星域", "铭匠", "SUNDAY"]
    res = session.scalars(select(Product).where(
        or_(*[Product.manufacturer.ilike(f"%{m}%") for m in mfgs])
    )).all()
    print(f"Total matching existing products: {len(res)}")
    for p in res:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | {p.product_line}")

    # Check names
    names = ["杰达", "卡戎", "奥伯龙", "希切尔", "阿斯加德", "瓦尔基里", "萨拉曼德", "诺姆", "赤鬼若", "天狗", "逍遥子", "猞猁", "嬴政"]
    res2 = session.scalars(select(Product).where(
        or_(*[Product.kit_name.ilike(f"%{n}%") for n in names])
    )).all()
    print(f"\nTotal matching names: {len(res2)}")
    for p in res2:
        print(f"[{p.manufacturer}] [{p.product_code}] {p.kit_name} | {p.product_line}")
