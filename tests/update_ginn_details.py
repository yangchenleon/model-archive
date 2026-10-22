import os
import sys
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product

updates = {
    "Z001R": {
        "kit_name": "金恩·红（角斗士/斯巴达）",
        "detail": "翻模MG 1/100比例，金恩角斗士（斯巴达式样）红色涂装。新规零件较多，附带金属色成型板件，风格厚重。",
    },
    "Z001O": {
        "kit_name": "金恩·橙（米盖尔·艾曼专用机）",
        "detail": "翻模MG 1/100比例，“黄昏魔弹”米盖尔·艾曼专用橙色涂装，套件追加专用防盾及标识。",
    },
}

with SessionLocal() as session:
    for code, info in updates.items():
        prod = session.scalars(
            select(Product).where(
                Product.manufacturer == "幻影模型",
                Product.product_code == code,
            )
        ).first()

        if prod:
            print(f"Updating [{prod.product_code}]:")
            print(f"  Old name:   {prod.kit_name}")
            print(f"  Old detail: {prod.detail}")
            prod.kit_name = info["kit_name"]
            prod.detail = info["detail"]
            print(f"  New name:   {prod.kit_name}")
            print(f"  New detail: {prod.detail}")
        else:
            print(f"Product [{code}] not found!")

    session.commit()
    print("\nCommit successful!")
