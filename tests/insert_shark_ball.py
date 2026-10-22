import os
import sys
import uuid
from pathlib import Path

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product

shark_ball = {
    "manufacturer": "钢铁模型",
    "product_code": "VN002W",
    "product_line": "MG",
    "kit_name": "鲨鱼铁球 / 卡版铁球（鲨鱼嘴水贴版）",
    "origin_type": "手动录入",
    "source": "手动录入",
    "detail": "模具沿用VN002卡铁球，核心骨架+桁架骨架+外甲三重结构一致。鲨鱼嘴/虎面图案靠水贴实现（非新规零件）。保留金属炮管、金色弹簧、三色可选细铁丝电缆、展示小地台及整备员小人。",
}

with SessionLocal() as session:
    existing = session.scalars(
        select(Product).where(
            Product.manufacturer == shark_ball["manufacturer"],
            Product.product_code == shark_ball["product_code"],
        )
    ).first()

    if existing:
        existing.kit_name = shark_ball["kit_name"]
        existing.product_line = shark_ball["product_line"]
        existing.origin_type = shark_ball["origin_type"]
        existing.source = shark_ball["source"]
        existing.detail = shark_ball["detail"]
        print(f"Updated existing: [{shark_ball['product_code']}] {shark_ball['kit_name']}")
    else:
        prod = Product(
            id=uuid.uuid4(),
            manufacturer=shark_ball["manufacturer"],
            product_code=shark_ball["product_code"],
            product_line=shark_ball["product_line"],
            origin_type=shark_ball["origin_type"],
            source=shark_ball["source"],
            kit_name=shark_ball["kit_name"],
            detail=shark_ball["detail"],
        )
        session.add(prod)
        print(f"Added new: [{shark_ball['product_code']}] {shark_ball['kit_name']}")

    session.commit()
    print("Committed successfully.")
