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

GAOGAO_PRODUCTS = [
    # ==========================================
    # MGSD 系列 (13 款)
    # ==========================================
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "巴巴托斯",
        "origin_type": "拼装模型",
        "detail": "2025年8月发售。原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "巴巴托斯（玄武色）",
        "origin_type": "拼装模型",
        "detail": "2026年1月/4月发售。玄武黑红特别配色修复版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "自由高达",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "自由高达（彩透版）",
        "origin_type": "拼装模型",
        "detail": "彩色透明限定版外甲",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "自由高达（樱花粉）",
        "origin_type": "拼装模型",
        "detail": "2026年4月发售。樱花粉特别配色修复版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "风灵高达",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "风灵高达（樱花粉）",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。樱花粉特别涂装版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "风灵高达（中国红）",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。中国红特别涂装版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "风灵高达（紫罗兰）",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。紫罗兰特别涂装版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达",
        "origin_type": "拼装模型",
        "detail": "2025年8月发售。原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达（白雪姬配色）",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。白雪姬风格纯白金色专属涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达（樱花粉配色）",
        "origin_type": "拼装模型",
        "detail": "2025年9月发售。樱花粉特别涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达（蓝白渐变配色）",
        "origin_type": "拼装模型",
        "detail": "2025年11月发售。蓝白渐变特别涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达（电镀紫配色）",
        "origin_type": "拼装模型",
        "detail": "2025年12月发售。电镀紫特别涂装限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "飞翼高达（鲁路修特别配色）",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。鲁路修联名特别涂装限定配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "命运高达",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "MGSD",
        "product_code": None,
        "kit_name": "命运高达（海涅配色）",
        "origin_type": "拼装模型",
        "detail": "海涅专属橙黄特别涂装配色",
        "source": "手动录入",
    },

    # ==========================================
    # RG 系列 (30 款)
    # ==========================================
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "拂晓高达",
        "origin_type": "拼装模型",
        "detail": "2026年3月发售。金色涂装通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "拂晓高达（白金配色）",
        "origin_type": "拼装模型",
        "detail": "2026年5月发售。白金涂装特别配色版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "神高达（修复版）",
        "origin_type": "拼装模型",
        "detail": "2026年2月发售。神高达关节强度及组合度修复改进版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "牛高达",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "牛高达（电镀版）",
        "origin_type": "拼装模型",
        "detail": "全机金属电镀工艺限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "牛高达（钛电镀版）",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。钛白电镀特别版（钛镀牛）",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "牛高达 HWS 装备配件包",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。重装牛高达 Heavy Weapons System 武器配件拓展包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "牛高达（HWS形态）",
        "origin_type": "拼装模型",
        "detail": "2025年9月发售。重装牛高达全装备同捆套装（含本体与HWS重装武装）",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈牛高达",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。福冈实物大ν高达涂装及长程浮游炮配置",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈牛高达（幻彩镭射版）",
        "origin_type": "拼装模型",
        "detail": "2025年12月发售。福冈牛高达幻彩镭射偏光涂层限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "元祖 2.0（原色版）",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。RG 2.0 原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "元祖 2.0（G3配色）",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。G3低可视度涂装特别配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "元祖 2.0（初音未来配色）",
        "origin_type": "拼装模型",
        "detail": "2026年3月发售。初音绿蓝涂装特别配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "元祖 2.0（九龙拳一配色+大阪世博配件包）",
        "origin_type": "拼装模型",
        "detail": "2026年4月发售。九龙拳一配色涂装，附带大阪世博配件包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "沙扎比（原版/原色）",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "沙扎比（彩透版）",
        "origin_type": "拼装模型",
        "detail": "2025年11月发售。彩色透明限定外甲",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "沙扎比（彩透电镀版）",
        "origin_type": "拼装模型",
        "detail": "2025年11月发售。彩色透明与电镀复合工艺限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "沙扎比（白沙/白灰双色板件）",
        "origin_type": "拼装模型",
        "detail": "2025年11月发售。白色沙扎比双色分色板件版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "沙扎比（板喷七彩银色）",
        "origin_type": "拼装模型",
        "detail": "板喷七彩幻彩钛银涂装限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈沙扎比",
        "origin_type": "拼装模型",
        "detail": "2025年11月/12月发售。福冈实物大样式特别版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈沙扎比（彩透电镀版）",
        "origin_type": "拼装模型",
        "detail": "2025年12月发售。福冈沙扎比彩色透明电镀限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈沙扎比蟹钳配件包",
        "origin_type": "拼装模型",
        "detail": "2025年12月发售。双角型机械臂浮游炮（蟹钳）拓展武器配件包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "福冈沙扎比蟹钳配件包（彩透电镀版）",
        "origin_type": "拼装模型",
        "detail": "2025年12月发售。彩色透明+电镀双角型蟹钳拓展配件包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "海牛高达",
        "origin_type": "拼装模型",
        "detail": "原色通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "海牛高达（钛镀紫）",
        "origin_type": "拼装模型",
        "detail": "钛电镀紫特别涂装限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "海牛高达（樱花粉）",
        "origin_type": "拼装模型",
        "detail": "樱花粉特别涂装限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "吉翁号（普通版）",
        "origin_type": "拼装模型",
        "detail": "普通通贩版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "吉翁号（豪华版-带特效件）",
        "origin_type": "拼装模型",
        "detail": "附带全套场景特效件豪华版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "吉翁号（彩透板喷版）",
        "origin_type": "拼装模型",
        "detail": "彩色透明与板喷复合工艺限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "RG",
        "product_code": None,
        "kit_name": "红龙异端",
        "origin_type": "拼装模型",
        "detail": "RG 比例红异端红龙形态",
        "source": "手动录入",
    },

    # ==========================================
    # HG 系列 (11 款)
    # ==========================================
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "大阪世博元祖",
        "origin_type": "拼装模型",
        "detail": "2026年2月发售。2025年大阪世博会限定涂装配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "大阪世博元祖（樱花粉限定）",
        "origin_type": "拼装模型",
        "detail": "2026年4月发售。2025年大阪世博会限定樱花粉配色",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "命运高达（彩透版）",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。HGCE 命运高达彩色透明限定版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "宙斯魅影（海涅机&宙斯魅影装备）",
        "origin_type": "拼装模型",
        "detail": "2025年10月发售。命运高达海涅专属配色机搭配宙斯魅影装备同捆套装",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "宙斯魅影（命运&宙斯魅影装备）",
        "origin_type": "拼装模型",
        "detail": "2025年7月发售。命运高达搭配宙斯魅影装备同捆套装",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "宙斯魅影装备（单体）",
        "origin_type": "拼装模型",
        "detail": "2025年7月发售。宙斯魅影重型武器装备单体拓展配件包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "正义魔蝎",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。正义魔蝎单体形态",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "正义魔蝎（骁骑配件包）",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。正义魔蝎搭配骁骑扩展配件包",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "正义魔蝎（魔蝎+骁骑配件包）",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。正义魔蝎本体与骁骑配件包同捆豪华套装",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "红龙异端（修复版）",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。HGCE 红异端红龙形态修复版",
        "source": "手动录入",
    },
    {
        "manufacturer": "高高",
        "product_line": "HG",
        "product_code": None,
        "kit_name": "骁骑配件包",
        "origin_type": "拼装模型",
        "detail": "2026年1月发售。骁骑战车通用拓展武器配件包",
        "source": "手动录入",
    },
]

from sqlalchemy import select, func, delete

def insert_or_update_products():
    created = 0
    updated = 0
    with SessionLocal.begin() as session:
        # Delete old combined entry and redundant space variants if exist
        session.execute(
            delete(Product).where(
                Product.manufacturer == "高高",
                Product.kit_name.in_([
                    "风灵高达（樱花粉/中国红/紫罗兰）",
                    "福冈沙扎比 蟹钳配件包",
                    "福冈沙扎比 蟹钳配件包（彩透电镀版）",
                    "牛高达（HWS 重牛）",
                ]),
            )
        )
        for item in GAOGAO_PRODUCTS:
            code = item["product_code"]
            stmt = select(Product).where(
                Product.manufacturer == item["manufacturer"],
                Product.product_line == item["product_line"],
                Product.product_code.is_(None) if code is None else Product.product_code == code,
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
        for pl in ["MGSD", "RG", "HG"]:
            prods = session.scalars(
                select(Product)
                .where(Product.manufacturer == "高高", Product.product_line == pl)
                .order_by(Product.kit_name)
            ).all()
            print(f"\n高高 [{pl}] 总数: {len(prods)} 款")
            for p in prods:
                print(f"  - {p.kit_name:32s} | detail: {p.detail or '-'}")

if __name__ == "__main__":
    insert_or_update_products()
    verify_inserted()
