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

entries = [
    # ==========================
    # 一、胶佬星人
    # ==========================
    {
        "manufacturer": "胶佬星人",
        "product_code": "01",
        "product_line": "1/100",
        "kit_name": "RGM-88X 杰达（普通型/设定色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "出自《机动战士Moon高达》过渡量产机，补全1/100无套件遗憾。"
            "精密刻线与独立骨架，配光束步枪、盾牌、光束军刀、专用地台支架与水贴，素组分色优秀高性价比。"
        ),
    },
    {
        "manufacturer": "胶佬星人",
        "product_code": "02",
        "product_line": "1/100",
        "kit_name": "RGM-88X 杰达（阿姆罗专用型/白紫红配色）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "阿姆罗测试机专属白紫红涂装。附带头部感应式蓝色LED磁吸发光灯组、多组替换手型、蛇骨可动支架与收纳地台。"
        ),
    },
    {
        "manufacturer": "胶佬星人",
        "product_code": "03",
        "product_line": "1/100",
        "kit_name": "杰达 加农型（Cannon Type）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "重火力支援型衍生机。新增肩部加农炮装备、重装甲外甲配件及武器挂架，强化了厚重感与火力感。"
        ),
    },

    # ==========================
    # 二、机核工业 MECHA CORE INDUSTRY
    # ==========================
    {
        "manufacturer": "机核工业",
        "product_code": "JH-001",
        "product_line": "1/100",
        "kit_name": "卡戎 CHARON（JH-001）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价159元，1/100比例（全高约26cm）。双层骨架，腿部/躯干/颈部多处液压杆联动。"
            "配精神力感应盾×4、光束剑×2、组合近战光剑×2、匕首×2、微型护盾×2；首批特典含蚀刻片、移印地台与荧光水贴等。"
        ),
    },
    {
        "manufacturer": "机核工业",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "天卫·奥伯龙 OBERON",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价约169元，1/100比例。金/白/灰主调（送全金板件与原色外甲），翅膀与裂甲联动展开。"
            "配6枚羽毛钢笔形浮游炮、环形地台、枪盾与光束大剑。翅膀根部偏脆需注意防断。"
        ),
    },
    {
        "manufacturer": "机核工业",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "奥伯龙 异色版（机核工业×小芒联名）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价168元，2026年4月出货。小芒联名换色版，采用新规头雕与胸部配件。"
        ),
    },
    {
        "manufacturer": "机核工业",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "奥伯龙·改",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价168元，2026年6月出货。蓝色系换色，重组配件（配浮游炮×6、复合式枪盾、光束大剑等）。"
        ),
    },
    {
        "manufacturer": "机核工业",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "地卫·希切尔 IXCHEL",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价139元（特惠99元），本体约22cm（含地台约47cm）。超可动骨架，配4枪4剑、手型与水贴。"
            "首批特典含预涂装升降甲板地台与粒子步枪。"
        ),
    },

    # ==========================
    # 三、伊达斯科技
    # ==========================
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "阿斯加德 ASGARD",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价199元，高约22cm（2024年12月）。合金关节+POM四层骨架，227处可动与29处展开，含800+零件。"
            "配双弹道步枪、等离子炮、长约21cm的支援机“诸神黄昏”。首发特典含黄色替换骨架+橙色外甲。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "阿斯加德 ASGARD（会场限定机械透明版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "会场限定机械透明外甲版本，透视展示四层复杂骨架与联动机械结构。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "阿斯加德 ASGARD（会场限定彩透版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "会场限定彩色透明外甲版本，兼顾分色层次与骨架内构透光观赏性。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "瓦尔基里 VALKYRIE",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价188元，全高约21cm（2025年7月）。锌合金+POM骨架，配D·FANG盾/大剑、双太刀、极光模式外甲×8、透明支架与地台水贴。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "瓦尔基里 VALKYRIE（WF限定机械透明版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "WF展会限定机械透明版本（约258元档），透明外甲透视展示锌合金+POM骨架与细节。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "瓦尔基里 VALKYRIE（WF限定全息影像版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "WF展会限定全息影像特殊质感版本（约258元档），呈现全息渐变光泽与未来科幻质感。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "萨拉曼德－火蛇 SALAMANDER",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "首批99元/现货128元，高约19cm重约254g（2026年1-2月）。磨砂外甲+大量合金关节，红闪粉能量斗篷，双面罩与可分拆大刀。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "萨拉曼德－火蛇（曜影版/抛光镀银）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "曜影换色版，抛光镀银钛金属质感涂装，定价188元，限量1500体。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "萨拉曼德－火蛇（暗影版/曜银抛光镀银）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "暗影版（曜银），抛光镀银钛金属质感深色涂装，定价188元，限量1500体。"
        ),
    },
    {
        "manufacturer": "伊达斯科技",
        "product_code": None,
        "product_line": "1/100",
        "kit_name": "诺姆 GNOME（量产型/队长机）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价168元，高约19cm（2026年7月）。队长机普通版量产机体，经实拍调深改色，质感表现优良。"
        ),
    },

    # ==========================
    # 四、铭匠传
    # ==========================
    {
        "manufacturer": "铭匠传",
        "product_code": None,
        "product_line": "国风机甲",
        "kit_name": "赤鬼若·清盛（初代）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "原价199元，高约23cm。成品一体骨架+预涂装，和风武士造型，附带大尺寸精致地台。"
        ),
    },
    {
        "manufacturer": "铭匠传",
        "product_code": None,
        "product_line": "国风机甲",
        "kit_name": "雪之章·雪鬼（赤鬼若限定换色版）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价188元（2025年4月）。白灰主调配红金喷涂板件，优化材质与松紧度，附不知火地台、赤鬼首浮游炮×2及特效件。"
        ),
    },
    {
        "manufacturer": "铭匠传",
        "product_code": None,
        "product_line": "国风机甲",
        "kit_name": "天狗判官·义经",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价188元，高约23cm（翼展66cm）。POM成品骨架+金属关节，三替换头雕与胸裙妖面，配太刀、锡杖、36cm阴阳团扇与高亮UV荧光件，4仓收纳地台。"
        ),
    },
    {
        "manufacturer": "铭匠传",
        "product_code": None,
        "product_line": "国风机甲",
        "kit_name": "逍遥子 XIAOYAOZI（×SUNDAY HOBBY）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价188元（2025年7月），高约23cm。道袍云纹太极八卦国风。成品合金骨架，配太乙机关瓠、风雨雷电四象剑（可组“道”）、莲花飞升地台与屏风。"
        ),
    },
    {
        "manufacturer": "铭匠传",
        "product_code": "REA-03",
        "product_line": "蓝鲸系列",
        "kit_name": "蓝鲸系列·猞猁 LYNX（REA-03）",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价158–178元，1/72比例（高约29cm）。写实科幻军武风，赛钢骨架，折叠式37cm超远程狙击轨道炮与步枪。附整备格纳库+发射台双地台与8个维修小人。"
        ),
    },
    {
        "manufacturer": "铭匠传",
        "product_code": None,
        "product_line": "国风机甲",
        "kit_name": "始皇帝·嬴政",
        "origin_type": "手动录入",
        "source": "手动录入",
        "detail": (
            "定价298元（2026年1月），高约25cm。81板/约1700零件重约5kg。合金+赛钢骨架，配玄鸟背包、秦王剑、玉玺、长城地台与全长1.1米机械巨龙（两种龙头四肢可换）。"
        ),
    },
]

with SessionLocal() as session:
    added = 0
    updated = 0
    for item in entries:
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
    print(f"\nExecution finished! Added: {added}, Updated: {updated}, Total: {len(entries)}")
