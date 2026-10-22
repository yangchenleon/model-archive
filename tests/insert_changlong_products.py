import os
import sys
from pathlib import Path

# Connect to database via Docker-mapped port if not already set
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://model_archive:model_archive_dev@127.0.0.1:15432/model_archive"

sys.path.insert(0, str(Path("backend").resolve()))

from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import Product

CHANGLONG_PRODUCTS = [
    # 5501: RG 元祖 2.0
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5501",
        "kit_name": "元祖 2.0（原色）",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5501",
        "kit_name": "元祖 2.0（基地配色）",
        "origin_type": "拼装模型",
        "detail": "高达基地限定实物涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5501",
        "kit_name": "元祖 2.0（九龙拳一配色）",
        "origin_type": "拼装模型",
        "detail": "九龙拳一涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5501",
        "kit_name": "元祖 2.0（彩透版）",
        "origin_type": "拼装模型",
        "detail": "彩色透明限定外甲",
        "source": "手动录入",
    },
    # 5502: RG 牛高达
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5502",
        "kit_name": "牛高达",
        "origin_type": "拼装模型",
        "detail": "原色版",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5502D",
        "kit_name": "牛高达（钛电镀版）",
        "origin_type": "拼装模型",
        "detail": "钛电镀牛",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5502 TD",
        "kit_name": "牛高达（彩透版）",
        "origin_type": "拼装模型",
        "detail": "彩色透明限定外甲",
        "source": "手动录入",
    },
    # 5503: RG 海牛高达
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5503",
        "kit_name": "海牛高达",
        "origin_type": "拼装模型",
        "detail": "原色版",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5503D",
        "kit_name": "海牛高达（钛电镀版）",
        "origin_type": "拼装模型",
        "detail": "钛电镀海牛",
        "source": "手动录入",
    },
    # 5504: RG 福冈牛高达
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5504",
        "kit_name": "福冈牛高达",
        "origin_type": "拼装模型",
        "detail": "福冈实物大ν高达涂装及长程浮游炮配置",
        "source": "手动录入",
    },
    # 5505: RG 飞翼零式
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5505",
        "kit_name": "飞翼零式",
        "origin_type": "拼装模型",
        "detail": "RG 飞翼零式高达 EW",
        "source": "手动录入",
    },
    # 5506: RG 拂晓高达
    {
        "manufacturer": "长龙",
        "product_line": "RG",
        "product_code": "5506",
        "kit_name": "拂晓高达",
        "origin_type": "拼装模型",
        "detail": "把万代的一体成型骨架改成全拼装",
        "source": "手动录入",
    },
    # 1001: MGSD 飞翼高达
    {
        "manufacturer": "长龙",
        "product_line": "MGSD",
        "product_code": "1001",
        "kit_name": "飞翼高达",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGSD",
        "product_code": "1001",
        "kit_name": "飞翼高达（蓝白渐变配色）",
        "origin_type": "拼装模型",
        "detail": "蓝白渐变配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGSD",
        "product_code": "1001",
        "kit_name": "飞翼高达（白雪姬配色）",
        "origin_type": "拼装模型",
        "detail": "E 板做了单独板喷，金色发色漂亮，预售半天就破 1500 件",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGSD",
        "product_code": "1001",
        "kit_name": "飞翼高达（黑色板喷/黑红）",
        "origin_type": "拼装模型",
        "detail": "大唐联名 / 渠道版，哑光+亮黑双黑配红，帅但拉胯",
        "source": "手动录入",
    },
    # 7701: MGEX 强袭自由
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7701",
        "kit_name": "强袭自由（原色）",
        "origin_type": "拼装模型",
        "detail": "原色版，附带光翼特效件",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7701",
        "kit_name": "强袭自由（午夜黑）",
        "origin_type": "拼装模型",
        "detail": "午夜黑配色，附带光翼特效件",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7701",
        "kit_name": "强袭自由（暮光白配色）",
        "origin_type": "拼装模型",
        "detail": "暮光白配色，附带光翼特效件",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7701 TD",
        "kit_name": "强袭自由（透明外甲版）",
        "origin_type": "拼装模型",
        "detail": "暮光白配色，无光翼特效件",
        "source": "手动录入",
    },
    # 7702: MGEX 独角兽
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7702",
        "kit_name": "独角兽",
        "origin_type": "拼装模型",
        "detail": "配备蓝牙控制灯组，后面都无灯组",
        "source": "手动录入",
    },
    # 7703: MG 卡版飞翼零式 EW
    {
        "manufacturer": "长龙",
        "product_line": "MG",
        "product_code": "7703",
        "kit_name": "卡版飞翼零式 EW",
        "origin_type": "拼装模型",
        "detail": "Ver.Ka 卡版飞翼零式",
        "source": "手动录入",
    },
    # 7705: MGEX 菲尼克斯
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7705",
        "kit_name": "菲尼克斯",
        "origin_type": "拼装模型",
        "detail": "原色金色版",
        "source": "手动录入",
    },
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7705",
        "kit_name": "菲尼克斯（黑仿MMJ配色）",
        "origin_type": "拼装模型",
        "detail": "黑仿MMJ配色",
        "source": "手动录入",
    },
    # 7706: MGEX 报丧女妖 命运女神
    {
        "manufacturer": "长龙",
        "product_line": "MGEX",
        "product_code": "7706",
        "kit_name": "报丧女妖 命运女神",
        "origin_type": "拼装模型",
        "detail": "报丧女妖二号机 命运女神",
        "source": "手动录入",
    },
    # 9901: MB 神意高达
    {
        "manufacturer": "长龙",
        "product_line": "MB",
        "product_code": "9901",
        "kit_name": "神意高达",
        "origin_type": "拼装模型",
        "detail": "长龙首次进军 MB 比例，预售约 288 元，属于刚落地阶段，强烈建议等实机评测再下手",
        "source": "手动录入",
    },
    # 9902: 放大RG 福冈牛
    {
        "manufacturer": "长龙",
        "product_line": "放大RG",
        "product_code": "9902",
        "kit_name": "福冈牛高达（放大版）",
        "origin_type": "拼装模型",
        "detail": "1/100 放大版 RG 福冈牛高达",
        "source": "手动录入",
    },
]

def insert_or_update_products():
    created = 0
    updated = 0
    with SessionLocal.begin() as session:
        for item in CHANGLONG_PRODUCTS:
            stmt = select(Product).where(
                Product.manufacturer == item["manufacturer"],
                Product.product_line == item["product_line"],
                Product.product_code == item["product_code"],
                Product.kit_name == item["kit_name"],
            )
            existing = session.scalar(stmt)
            if existing:
                existing.detail = item["detail"]
                existing.origin_type = item["origin_type"]
                existing.source = item["source"]
                updated += 1
            else:
                product = Product(**item)
                session.add(product)
                created += 1

    print(f"Insert/Update finished: created={created}, updated={updated}")

def verify_inserted():
    with SessionLocal() as session:
        cl_products = session.scalars(
            select(Product)
            .where(Product.manufacturer == "长龙")
            .order_by(Product.product_line, Product.product_code, Product.kit_name)
        ).all()
        print(f"\nTotal '长龙' products in DB now: {len(cl_products)}")
        for p in cl_products:
            print(f"  [{p.product_line:5s}] [{p.product_code:8s}] {p.kit_name:24s} | detail: {p.detail or '-'}")

if __name__ == "__main__":
    insert_or_update_products()
    verify_inserted()
