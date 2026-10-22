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

new_products = [
    {
        "product_code": "8839",
        "manufacturer": "大班",
        "product_line": "88系列",
        "origin_type": "手动录入",
        "source": "手动录入",
        "kit_name": "MB 神意高达",
        "detail": (
            "参考定价约149元。仿MB样式，带超合金件与弹簧联动结构。"
            "亮点在于藏蓝色外甲三层分色猛、金属色板喷与预涂装到位、配件丰富（8支浮游炮+发射特效件、光剑渐变特效件、地台支架）。"
            "主要问题是深色零件水纹明显且易缩胶，肩腿关节偏松，大龟壳背包沉重塑料骨架站不住必须上支架，细小分色件多拼装抠手，侧裙甲较松。"
        ),
    },
    {
        "product_code": "8835",
        "manufacturer": "大班",
        "product_line": "88系列",
        "origin_type": "手动录入",
        "source": "手动录入",
        "kit_name": "MB 嫣红强袭（合金骨架版）",
        "detail": (
            "定价约268元。仿MB样式，合金骨架搭配凤装背包，新规头雕。总评约3.5分。"
            "问题在于新头雕显脸长且天线需调正，与万代MB相比整体色调粉色过重；"
            "预组装铁骨影响后背背包安装，后裙甲易掉、肩膀桩位插不到底、手臂平转易脱出；"
            "背包顶端小机翼及外甲夹紧前零件极易掉件。"
        ),
    },
    {
        "product_code": "6660",
        "manufacturer": "大班",
        "product_line": "66系列",
        "origin_type": "手动录入",
        "source": "手动录入",
        "kit_name": "天蚀高达+雷神装备",
        "detail": (
            "拼多多券后约120–140元。翻模万代MG天蚀高达+雷神装备（6658为单本体版）。"
            "最大卖点为翻自万代的完整变形骨架设计，胸口开口笑较6658有优化。"
            "主要问题是关节普遍偏松，高达形态下肩膀松垮、胯腿因变形机构站立吃力，装背包后撑不住必须上支架；"
            "头部两侧天线易掉建议粘死，脚腕两侧安装困难费手。"
        ),
    },
]

with SessionLocal() as session:
    for item in new_products:
        existing = session.scalars(
            select(Product).where(
                Product.manufacturer == item["manufacturer"],
                Product.product_code == item["product_code"],
            )
        ).first()

        if existing:
            print(f"Updating existing product [{item['product_code']}] {existing.kit_name}")
            existing.kit_name = item["kit_name"]
            existing.product_line = item["product_line"]
            existing.origin_type = item["origin_type"]
            existing.source = item["source"]
            existing.detail = item["detail"]
        else:
            print(f"Adding new product [{item['product_code']}] {item['kit_name']}")
            prod = Product(
                id=uuid.uuid4(),
                manufacturer=item["manufacturer"],
                product_code=item["product_code"],
                product_line=item["product_line"],
                origin_type=item["origin_type"],
                source=item["source"],
                kit_name=item["kit_name"],
                detail=item["detail"],
            )
            session.add(prod)

    session.commit()
    print("Changes committed successfully.")
