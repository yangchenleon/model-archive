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

new_entries = [
    # ==========================
    # 幻影模型 (Phantom Model)
    # ==========================
    # 扎古系列
    {
        "manufacturer": "幻影模型",
        "product_code": "2001B",
        "product_line": "扎古系列",
        "kit_name": "斩击型扎古幻影（伊扎克专用机/蓝）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第一批次（代号337900）。翻模MG 1/100比例，伊扎克天蓝色涂装，配备斩击型巨斧装备背包。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001G",
        "product_line": "扎古系列",
        "kit_name": "瞬发型扎古勇士（量产机/绿）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第二批次（代号347427）。绿色杂兵量产配色，搭载瞬发型高机动推进背包。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001GA",
        "product_line": "扎古系列",
        "kit_name": "炮击型扎古勇士（量产机/绿）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第二批次。绿色杂兵量产配色，搭载长距离光束炮炮击背包。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001BL",
        "product_line": "扎古系列",
        "kit_name": "炮击型扎古勇士（迪亚哥专用机/黑）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第三批次。迪亚哥专用黑色/暗色涂装，搭载长距离炮击背包装备。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001O",
        "product_line": "扎古系列",
        "kit_name": "炮击型扎古勇士（海涅专用机/橙）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第三批次。海涅标志性橙色涂装配炮击背包，为国内模型厂商原创配色设定。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001CT",
        "product_line": "扎古系列",
        "kit_name": "炮击型扎古勇士（露娜玛利亚专用机/红/双外甲）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第四批次（代号359961）。露娜玛利亚红机炮击型，附带彩透与实色双套外甲。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001P",
        "product_line": "扎古系列",
        "kit_name": "瞬发型扎古勇士（雷专用机/白）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第四批次（代号353424）。雷·扎·巴雷尔专用白色涂装，搭载瞬发型背包。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001K",
        "product_line": "扎古系列",
        "kit_name": "扎古勇士（米娅演唱会版/粉）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第五批次（代号353772）。米娅演唱会粉色涂装，附带专属图案贴纸。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001BLA",
        "product_line": "扎古系列",
        "kit_name": "扎古勇士本体（黑色无装备版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第5.5批次。纯黑色扎古勇士素体，不附带额外武装背包。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "2001BG",
        "product_line": "扎古系列",
        "kit_name": "斩击型扎古勇士（量产机/绿）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "幻影模型第六批次。绿色量产型斩击背包形态，至此绿色杂兵扎古三种背包形态出齐。",
    },
    # 厄运式系列
    {
        "manufacturer": "幻影模型",
        "product_code": "G001",
        "product_line": "厄运式系列",
        "kit_name": "进阶型厄运式（黑色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代MG 1/100比例，进阶型GN-X（Advanced GN-X）黑色涂装机。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "G002",
        "product_line": "厄运式系列",
        "kit_name": "进阶型厄运式（红色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代MG 1/100比例，进阶型GN-X红色涂装机（黛博拉专用配色风格）。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "G003",
        "product_line": "厄运式系列",
        "kit_name": "白虎星 厄运式Ⅳ（A-Laws红）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模MG 1/100比例，白虎星厄运式Ⅳ型，A-Laws专属红灰配色。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "G004",
        "product_line": "厄运式系列",
        "kit_name": "白虎星 厄运式Ⅳ（地球联邦军蓝）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模MG 1/100比例，白虎星厄运式Ⅳ型，地球联邦正规军蓝白配色。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "G005",
        "product_line": "厄运式系列",
        "kit_name": "厄运式 GN-X（标准量产型）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代MG 1/100比例，基础款GN-X标准量产机型。",
    },
    # 金恩系列
    {
        "manufacturer": "幻影模型",
        "product_code": "Z001",
        "product_line": "金恩系列",
        "kit_name": "金恩（标准灰/量产型）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模万代MG 1/100比例，扎夫特主力机动战士金恩标准灰色量产版。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "Z001R",
        "product_line": "金恩系列",
        "kit_name": "金恩·红（角斗士/斯巴达）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模MG 1/100比例，金恩角斗士（斯巴达式样）红色涂装。新规零件较多，附带金属色成型板件，风格厚重。",
    },
    {
        "manufacturer": "幻影模型",
        "product_code": "Z001O",
        "product_line": "金恩系列",
        "kit_name": "金恩·橙（米盖尔·艾曼专用机）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": "翻模MG 1/100比例，“黄昏魔弹”米盖尔·艾曼专用橙色涂装，套件追加专用防盾及标识。",
    },

    # ==========================
    # 雷恩模型 (Reinn Model)
    # ==========================
    {
        "manufacturer": "雷恩模型",
        "product_code": "ZG-001",
        "product_line": "MG",
        "kit_name": "精神力扎古（普版/基准款）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价178元（券后130–150元），2025年4月出货。翻模MG雷霆宙域高机动型扎古“精神力扎古”，体积巨大纵深横跨达50-60cm的“柜霸”。"
            "动力管采用软胶套+合金弹簧还原质感，沿用扎古2.0骨架。缺点是表面较油、喷口屎黄成型色需补色、关节紧松矛盾、外甲干涉基本偏站尸。"
        ),
    },
    {
        "manufacturer": "雷恩模型",
        "product_code": "ZG-002",
        "product_line": "MG",
        "kit_name": "精神力扎古（战损版/最终决战Ver.）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "翻模万代PB限定“最终决战版”。减配普版部分巨型武器，附带FA-78全装甲高达战损替换件与专属战损地台。"
            "外甲发油细节偏肉，附带一大张DIY战损水贴（曲面贴合难建议手涂做旧），软胶管易炸口，造型手PC精度差易脱出，侧裙甲易掉。"
        ),
    },
    {
        "manufacturer": "雷恩模型",
        "product_code": "ZG-003",
        "product_line": "MG",
        "kit_name": "精神力扎古（彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "售价约136元，配置与普版一致。彩透零件主要在深蓝骨架件、部分武器与燃料罐支架，部分位置为珠光实色；"
            "深蓝透明度偏低发闷，珠光件水纹较重。性价比高但非全通透外甲，适合当普版平替或喷涂底子。"
        ),
    },
    {
        "manufacturer": "雷恩模型",
        "product_code": "ZG-004",
        "product_line": "MG",
        "kit_name": "雷霆宙域量产型扎古Ⅱ（配巨型狙击炮/狙击套）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价148元。精神力扎古同模换色，精简武装，核心卖点为原创全长巨型狙击炮（配3颗磁控灯组、4种光效、液压脚架与四臂联动）。"
            "本体塑料较硬脆易开裂，腿部侧裙易掉，属于“为大炮买单”的偏科套件。"
        ),
    },

    # ==========================
    # 钢铁模型 (Steel Model)
    # ==========================
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN001",
        "product_line": "MG",
        "kit_name": "钢坦克（普版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "翻模万代MG钢坦克，内构设计优秀骨架细节丰富。附赠金属炮管、成品履带+拼装履带双版本、LED头灯。"
            "组合度良好，个别位置偏紧需扩孔，腰部略松，KO中属上游水准（评分约8.4/10）。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN001T",
        "product_line": "MG",
        "kit_name": "钢坦克（彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "钢坦克彩透独立版本。透明件偏半透质感，蓝色略有浑浊，部分零件有荧光反应。"
            "附金属炮管与LED头灯，内构精细，笔涂后展示观赏性强。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002",
        "product_line": "MG",
        "kit_name": "陆战铁球 / 卡版铁球（普版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "翻模万代MG铁球Ver.Ka，核心骨架+桁架骨架+外甲三层结构。附金属炮管、弹簧、三色电缆与展示支架、小人。"
            "内构细节丰富适合笔涂，但骨架组合度一般，支架固定不稳，几乎无可动，偏桌面摆件。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002T",
        "product_line": "MG",
        "kit_name": "陆战铁球 / 卡版铁球（彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "卡版铁球彩透独立版本。半透外甲质感，部分零件具荧光反应，适合笔涂内构骨架透光展示。配金属炮管与电缆。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002G",
        "product_line": "MG",
        "kit_name": "多足铁球 / 铁球K型（普版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "08MS小队版多足铁球（铁球K型），四条机械腿+双管武器，附替换件支持一盒双形态切换为卡版铁球。"
            "金属管、软胶管与电线细节丰富。缺点是部分水口明显，外甲缝隙偏大。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002GT",
        "product_line": "MG",
        "kit_name": "多足铁球 / 铁球K型（彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "多足铁球K型彩透独立版本。半透外甲，四机械腿机械感强，支持双形态切换，荧光透光展示效果出众。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002O",
        "product_line": "MG",
        "kit_name": "橙铁球（普版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "售价约66元。与铁球K型同模具，橙灰色配色，零件手感偏软。废件可还原普通铁球形态，性价比尚可。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002OT",
        "product_line": "MG",
        "kit_name": "橙铁球（彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "橙铁球彩透独立版本。橙色半透明外甲，可透视内部机械骨架，废件支持双形态，桌面摆件观赏性高。"
        ),
    },
    {
        "manufacturer": "钢铁模型",
        "product_code": "VN002W",
        "product_line": "MG",
        "kit_name": "鲨鱼铁球 / 卡版铁球（鲨鱼嘴水贴版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "模具沿用VN002卡铁球，核心骨架+桁架骨架+外甲三重结构一致。鲨鱼嘴/虎面图案靠水贴实现（非新规零件）。"
            "保留金属炮管、金色弹簧、三色可选细铁丝电缆、展示小地台及整备员小人。"
        ),
    },
]

with SessionLocal() as session:
    added = 0
    updated = 0
    for item in new_entries:
        existing = session.scalars(
            select(Product).where(
                Product.manufacturer == item["manufacturer"],
                Product.product_code == item["product_code"],
            )
        ).first()

        if existing:
            existing.kit_name = item["kit_name"]
            existing.product_line = item["product_line"]
            existing.origin_type = item["origin_type"]
            existing.source = item["source"]
            existing.detail = item["detail"]
            updated += 1
            print(f"Updated: [{item['manufacturer']}] [{item['product_code']}] {item['kit_name']}")
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
            print(f"Added:   [{item['manufacturer']}] [{item['product_code']}] {item['kit_name']}")

    session.commit()
    print(f"\nExecution finished! Added: {added}, Updated: {updated}, Total: {len(new_entries)}")
