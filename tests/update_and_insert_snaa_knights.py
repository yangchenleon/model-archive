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

knights_data = [
    {
        "product_code": "01",
        "kit_name": "雷鸣收割者·格雷斯",
        "detail": (
            "2024年2月出货，首发定价39元（市价约60–70元）。系列开山作，紫黄配色灵活型女性驾驶员机体。"
            "完整骨架可动逆天（双臂可抱胸、弯腰幅度大），分色优秀无需补色，性价比极高。"
            "缺点是板件材质偏软易出白痕，外甲偏暗，部分关节过紧，且有机体缝合感。"
        ),
    },
    {
        "product_code": "02",
        "kit_name": "灵皇守护者·高文",
        "detail": (
            "2024年7月出货，首发定价43元（市价约50元）。白蓝配色，核心亮点为背部20cm宽蓝色光翼特效件（透明锐度高、闪亮度足），造型帅气。"
            "缺点是手臂旋转需先上抬，盾牌握持卡扣角度怪异需侧扣，骨架组合度偏紧。"
        ),
    },
    {
        "product_code": "02A",
        "kit_name": "灵皇守护者·高文（KK版）",
        "detail": (
            "2024年7月出货，定价48元（市价约60元）。设计师特别换色版，采用浅灰+金配色，光翼特效件升级为深蓝色。"
            "仅为换色无新规零件。"
        ),
    },
    {
        "product_code": "03",
        "kit_name": "神盾骑士·阿基里斯",
        "detail": (
            "2024年11月出货，首发定价40元（市价溢价至80–100元）。紫白配色攻防一体机，具备双形态切换玩法，配双剑双盾及机械臂挂架，刻线细节丰富，战斗姿态紧实。"
            "缺点是四肢关节摩擦力极大把玩易磨漆，面罩替换需拆侧甲，新手拼装体验偏硬核。"
        ),
    },
    {
        "product_code": "04",
        "kit_name": "钢镰·凯",
        "detail": (
            "2024年12月出货，定价45元（市价约60–75元）。白灰金配色，配主武器巨型镰刀及两把副镰，标配专属支架。造型霸气，可动继承前作。"
            "缺点是板件排版空位较多，部分水口不合理，透明披风边缘水口过大易剪崩，关节偏紧。"
        ),
    },
    {
        "product_code": "05",
        "kit_name": "巨鸣斧·兰斯洛特",
        "detail": (
            "2025年1月出货，定价45元（市价约60–85元）。疾风三骑士队长机，蓝白黑金配色，标志性牛角头盔。巨斧细节丰富带手柄秘文，牛头透明披风拉风。"
            "缺点是设计缝合感较强，手臂金色外甲干扰手型握持，透明披风水口易剪崩。"
        ),
    },
    {
        "product_code": "06",
        "kit_name": "巨神剑·特里斯坦",
        "detail": (
            "2025年7月出货，定价50元（市价约70–90元）。系列集大成之作，蓝白红配色刻金色凯尔特战纹。新规骨架改用金色预涂零件，大面积隐藏水口，松紧适中单手托巨剑无压力。"
            "配备泰坦巨剑、誓约之剑、如尼符文盾与透明脉冲披风。"
        ),
    },
    {
        "product_code": "07",
        "kit_name": "神器共鸣者·帕西瓦尔（单体版）",
        "detail": (
            "2025年11月发布/2026年1月出货单体版，定价55元（市价约60元）。圣域系列轻型速度机，白蓝紫金配色。附带双权杖、觉醒粒子披风、七把专属武器与环形特效件，分色到位。"
            "缺点是板件多拼装耗时，部分武器挂点偏松。"
        ),
    },
    {
        "product_code": "07A",
        "kit_name": "神器共鸣者·帕西瓦尔（豪华版）",
        "detail": (
            "2025年11月出货，定价72元（市价约85元）。21块板件系列最大规格。在单体版基础上额外增配专属地台及环形剑阵支架，可完整摆出环形剑阵仪式感拉满，豪华版性价比极高。"
            "缺点是拼装耗时长，部分武器挂点偏松。"
        ),
    },
    {
        "product_code": "08",
        "kit_name": "灵枪·马尔洛克",
        "detail": (
            "2026年1月出货，定价55元（市价约55–65元）。红白灰配色，持可变形骑枪（射击/近战）与破壁之斧。腰部双段转轴设计、肩部可外拉、腿部推进器内缩联动，新规骨架可动与用料触感明显提升，拍照出片。"
        ),
    },
    {
        "product_code": "09",
        "kit_name": "狂暴战锤·加拉哈德",
        "detail": (
            "官方定价69元，2026年5月出货，高约18cm。圆桌骑士团第九弹，力量型重装战士。灰白+灰蓝配色搭配金色板喷预涂件。"
            "搭载全新规骨架，可动性优异；配备战锤与战斧。虽在系列中定价较高但货量充足。"
        ),
    },
    {
        "product_code": "10",
        "kit_name": "爆裂狮·贝狄威尔",
        "detail": (
            "官方定价72元，2026年7月出货。圆桌骑士团第十弹，为系列已知最新机体。定价72元看齐帕西瓦尔豪华版，预计配备丰富武装与联动玩法。"
        ),
    },
]

with SessionLocal() as session:
    added = 0
    updated = 0
    for item in knights_data:
        existing = session.scalars(
            select(Product).where(
                Product.manufacturer == "SNAA",
                Product.product_line == "圆桌骑士团系列",
                Product.product_code == item["product_code"],
            )
        ).first()

        if existing:
            existing.kit_name = item["kit_name"]
            existing.detail = item["detail"]
            updated += 1
            print(f"Updated: [{item['product_code']}] {item['kit_name']}")
        else:
            prod = Product(
                id=uuid.uuid4(),
                manufacturer="SNAA",
                product_code=item["product_code"],
                product_line="圆桌骑士团系列",
                origin_type="手动录入",
                source="手动录入",
                kit_name=item["kit_name"],
                detail=item["detail"],
            )
            session.add(prod)
            added += 1
            print(f"Added:   [{item['product_code']}] {item['kit_name']}")

    session.commit()
    print(f"\nExecution completed! Added: {added}, Updated: {updated}, Total: {len(knights_data)}")
