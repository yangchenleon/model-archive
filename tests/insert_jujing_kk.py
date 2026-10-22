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
    # ==========================
    # 聚匠模型
    # ==========================
    {
        "manufacturer": "聚匠模型",
        "product_code": "HGBF-49",
        "product_line": "HGBF",
        "kit_name": "猫耳00Q（西亚量子型/原色绿）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "基于万代HGBF 00西亚量子型（猫耳00Q）翻模，原色浅绿配色，附带猫猫水贴，组合度较丝滑。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": "HGBF-49",
        "product_line": "HGBF",
        "kit_name": "猫耳00Q（粉色版）[原创]",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "聚匠原创粉色涂装猫耳00Q，附带猫猫图案水贴。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": "HGBF-49",
        "product_line": "HGBF",
        "kit_name": "猫耳00Q（深绿版）[原创]",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "聚匠原创深绿配色猫耳00Q，附带猫猫图案水贴。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "月高达（原色版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代HGUC月高达。刻线更深更锐利，无需渗线即可有良好层次感；但塑料材质偏脆，承力轴与连接处需防断裂。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "月高达（附长枪配件版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "HGUC月高达追加长光束步枪/长枪武器配件包版本。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "巴尔基尔（原色版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代PB限定HGUC巴尔基尔（沙扎比原型机），原色紫灰涂装，大腿根部结构有微调优化。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "巴尔基尔（沙扎比红配色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "巴尔基尔红色特殊涂装版，致敬沙扎比标志性红色涂装。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "MG",
        "kit_name": "倒A高达（带月光蝶特效件）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代MG 1/100倒A高达，附带月光蝶特效件。针对原版部分插桩与关节做了针对性紧固优化，平价入门款。",
    },
    {
        "manufacturer": "聚匠模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "柯西高达",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代HGUC柯西高达。优化了大臂自动脱出与水纹问题，分件体积大，为该厂口碑较好的热门款。",
    },

    # ==========================
    # KK模型
    # ==========================
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "陆战型高达",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代HGUC 1/144陆战型高达，亲民白菜价，适合大量量产搭配场景制作与练手改造。",
    },
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "陆战型吉姆",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代HGUC 1/144陆战型吉姆，高性价比量产机体，适合微缩场景与批量站队。",
    },
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "陆战型高达（KFC配色版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "陆战型高达肯德基KFC风格红白联名限定涂装配色款。",
    },
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "陆战型空降背包配件包",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "陆战机体适用的降落伞空降背包配件包，可搭载于陆战高达/吉姆背部还原空降作战姿态。",
    },
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "陆战型吉姆（奴隶幽灵小队/驭灵配色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "高达外传特战队“奴隶幽灵小队（驭灵小队）”战术夜战深色涂装陆战吉姆。",
    },
    {
        "manufacturer": "KK模型",
        "product_code": None,
        "product_line": "HGUC",
        "kit_name": "奴隶幽灵小队套装（驭灵小队）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "奴隶幽灵特装小队（驭灵小队）战术机体与特种装备组合套件。",
    },
]

with SessionLocal() as session:
    added = 0
    updated = 0
    for item in new_products:
        existing = session.scalars(
            select(Product).where(
                Product.manufacturer == item["manufacturer"],
                Product.kit_name == item["kit_name"],
            )
        ).first()

        if existing:
            existing.product_code = item["product_code"]
            existing.product_line = item["product_line"]
            existing.origin_type = item["origin_type"]
            existing.source = item["source"]
            existing.detail = item["detail"]
            updated += 1
            print(f"Updated: [{item['manufacturer']}] {item['kit_name']}")
        else:
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
            added += 1
            print(f"Added:   [{item['manufacturer']}] {item['kit_name']}")

    session.commit()
    print(f"\nFinished! Added: {added}, Updated: {updated}, Total: {len(new_products)}")
