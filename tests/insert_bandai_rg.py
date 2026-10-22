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

bandai_rg_list = [
    # 早期一体成型骨架时代（2010–2014）
    {
        "product_code": "01",
        "kit_name": "RX-78-2 高达",
        "detail": "2010年7月发售，售价2500日元。早期一体成型骨架开山作，细节丰富但骨架存在严重软骨病，RG 2.0推出后基本淘汰。",
    },
    {
        "product_code": "02",
        "kit_name": "MS-06S 夏亚专用扎古II",
        "detail": "2010年11月发售，售价2500日元。外形帅气但一体骨架偏软易断腿，动力管安装繁琐体验较差。",
    },
    {
        "product_code": "03",
        "kit_name": "GAT-X105 空战型强袭高达",
        "detail": "2011年4月发售，售价2500日元。胯部球形关节极软，大背包无法自立需依赖支架支撑。",
    },
    {
        "product_code": "04",
        "kit_name": "MS-06F 量产型扎古II",
        "detail": "2011年7月发售，售价2500日元。与RG02基本同模换色，一体骨架软骨问题相同。",
    },
    {
        "product_code": "05",
        "kit_name": "ZGMF-X10A 自由高达",
        "detail": "2011年11月发售，售价2500日元。通用骨架导致掉件较多，翅膀大背包需支架辅助支撑。",
    },
    {
        "product_code": "06",
        "kit_name": "FX-550 空中霸王+强袭炮击/剑装背包",
        "detail": "2012年2月发售，售价2500日元。无一体骨架，但受搭配的强袭本体素质拖累，性价比一般。",
    },
    {
        "product_code": "07",
        "kit_name": "RX-178 高达Mk-Ⅱ（提坦斯）",
        "detail": "2012年4月发售，售价2500日元。早期RG口碑最佳之一，骨架硬朗扎实、无沉重大背包，把持力度好。",
    },
    {
        "product_code": "08",
        "kit_name": "RX-178 高达Mk-Ⅱ（奥古）",
        "detail": "2012年5月发售，售价2500日元。与RG07同骨架仅配色不同，结构稳固同样高评价推荐。",
    },
    {
        "product_code": "09",
        "kit_name": "ZGMF-X09A 正义高达",
        "detail": "2012年7月发售，售价2500日元。与自由同通用骨架，存在掉件与大背包自立困难问题。",
    },
    {
        "product_code": "10",
        "kit_name": "MSZ-006 Z高达",
        "detail": "2012年11月发售，售价3000日元。完整变形机构极脆，变形易损被戏称寿命一次，不变形站姿尚可。",
    },
    {
        "product_code": "11",
        "kit_name": "ZGMF-X42S 命运高达",
        "detail": "2013年4月发售，售价2500日元。沿用SEED通用骨架，关节偏松易掉件，背部重心不稳。",
    },
    {
        "product_code": "12",
        "kit_name": "RX-78GP01 玉兰（陆战型）",
        "detail": "2013年7月发售，售价2500日元。冷门佳作，小体积结构完整紧致，早期RG中少数可稳定把玩的款式。",
    },
    {
        "product_code": "13",
        "kit_name": "RX-78GP01-Fb 玉兰（宇宙型）",
        "detail": "2013年7月发售，售价2500日元。略逊于陆战型，推进器对重心影响大，腰部核心机链接易脱出。",
    },
    {
        "product_code": "14",
        "kit_name": "ZGMF-X20A 强袭自由高达",
        "detail": "2013年11月发售，售价3000日元。同SEED系通用骨架，金色关节偏软易掉件，大翅膀必须上支架。",
    },

    # 过渡期（2014–2017）
    {
        "product_code": "15",
        "kit_name": "GN-001 能天使高达",
        "detail": "2014年4月发售，售价2500日元。软骨问题主要在胯关节，存在天蚕腿和裙甲干涉，站姿造型尚可。",
    },
    {
        "product_code": "16",
        "kit_name": "MSM-07S 夏亚专用魔蟹",
        "detail": "2014年7月发售，售价2500日元。RG通贩唯一水产，四肢多段关节偏软，搭配支架可玩性尚可。",
    },
    {
        "product_code": "17",
        "kit_name": "XXXG-00W0 零式飞翼高达EW",
        "detail": "2014年12月发售，售价2500日元。掉毛本体尚可，但脚后跟与轮子易掉件，手腕支撑力偏软需支架。",
    },
    {
        "product_code": "18",
        "kit_name": "GN-0000+GNR-010 00 RAISER",
        "detail": "2015年4月发售，售价3000日元。大量武装与双炉背包对一体成型骨架负担过重，勉强自主站立。",
    },
    {
        "product_code": "19",
        "kit_name": "MBF-P02 异端高达红色机",
        "detail": "2015年8月发售，售价2500日元。多色成型骨架+黑色拉丝外甲质感好，但关节偏松问题依旧存在。",
    },
    {
        "product_code": "20",
        "kit_name": "XXXG-01W 飞翼高达EW",
        "detail": "2016年1月发售，售价2500日元。关节松软易掉件，大背包后倾严重，基本为支架展示款。",
    },
    {
        "product_code": "21",
        "kit_name": "GNT-0000 量子型00",
        "detail": "2016年5月发售，售价2500日元。老RG集大成之作，造型满分，骨架有所优化，适度加固后把玩手感不错。",
    },
    {
        "product_code": "22",
        "kit_name": "MSN-06S 新安洲",
        "detail": "2016年8月发售，售价3800日元。套用Mk-Ⅱ骨架难以支撑庞大外甲导致整体松散，亮光漆与金色电镀也难掩结构硬伤。",
    },
    {
        "product_code": "23",
        "kit_name": "GAT-X105B/FP 创制强袭高达全装备",
        "detail": "2016年12月发售，售价2500日元。骨架未变沿用老强袭底子，关节偏软易掉件，表现平淡。",
    },
    {
        "product_code": "24",
        "kit_name": "MBF-P01-Re2 异端高达金色机天·蜜纳",
        "detail": "2017年3月发售，售价3000日元。亮黑外甲帅气，但金色成型色水纹拉低质感，关节偏松不适合重度把玩。",
    },

    # 拼装骨架时代（2017–2021）
    {
        "product_code": "25",
        "kit_name": "RX-0 独角兽高达",
        "detail": "2017年8月发售，售价3800日元。拼装骨架时代开端，变身NT-D机构精妙无需替换件，注意肩部关节过紧防扭断。",
    },
    {
        "product_code": "26",
        "kit_name": "MS-06R-2 强尼莱登专用高机动扎古II",
        "detail": "2017年11月发售，售价3000日元。仍沿用早期扎古一体骨架，载具配件较少，性价比不高。",
    },
    {
        "product_code": "27",
        "kit_name": "RX-0[N] 报丧女妖·命运女神",
        "detail": "2018年2月发售，售价4000日元。与独角兽同骨架，狮鬃武装霸气，整体结构稳定素质出众。",
    },
    {
        "product_code": "28",
        "kit_name": "OZ-00MS 多鲁基斯EW",
        "detail": "2018年4月发售，售价2500日元。RG分水岭，取消一体骨架改全新拼装骨架，比例优异结构极其稳固，高性价比神作。",
    },
    {
        "product_code": "29",
        "kit_name": "MSN-04 沙扎比",
        "detail": "2018年8月发售，售价4500日元。“RG四大天王”之一。体积巨大装甲联动丰富，注意脚掌水口与肩膀关节受力。",
    },
    {
        "product_code": "30",
        "kit_name": "RX-0 全装备独角兽高达（最终决战式样）",
        "detail": "2018年12月发售，售价5400日元。武器库级别海量配件，拼装骨架把玩松紧度优于卡版，性价比高。",
    },
    {
        "product_code": "31",
        "kit_name": "XM-X1 海盗高达X1",
        "detail": "2019年5月发售，售价2500日元。极限小比例精密机械构造，自带ABC披风且武器丰富，零件细小拼装需细致。",
    },
    {
        "product_code": "32",
        "kit_name": "RX-93 ν高达",
        "detail": "2019年8月发售，售价4200日元。“RG四大天王”之一。人手一台的胶圈神物，骨架设计教科书级别，分件与稳定性巅峰。",
    },
    {
        "product_code": "33",
        "kit_name": "ZGMF-X56S/α 威力型脉冲高达",
        "detail": "2020年4月发售，售价3000日元。分离合体玩法还原到位，背包机体稳固自立，关节阻尼感好。",
    },
    {
        "product_code": "34",
        "kit_name": "MSN-02 吉翁号",
        "detail": "2021年1月发售，售价5500日元。“RG四大天王”之一。细节刻画无敌，全可动手指，机械感拉满的高分神作。",
    },
    {
        "product_code": "35",
        "kit_name": "XXXG-01W 飞翼高达（TV版）",
        "detail": "2021年6月发售，售价3200日元。性价比之王，背包展开玩法帅气，还原鸟形态变形，骨架扎实。",
    },
    {
        "product_code": "36",
        "kit_name": "RX-93-ν-2 Hi-ν高达",
        "detail": "2021年9月发售，售价4500日元。“RG四大天王”之一。肌肉线条干练，浮游炮卡扣稳定性超越牛高达，天花板级产品。",
    },

    # 成熟期（2022–2025）
    {
        "product_code": "37",
        "kit_name": "GF13-017NJⅡ 神高达",
        "detail": "2022年8月发售，售价3500日元。超可动格斗骨架配置，自带日轮光环特效件，把玩与可动体验极佳。",
    },
    {
        "product_code": "38",
        "kit_name": "OZ-13MS 艾比安高达",
        "detail": "2023年9月发售，售价4620日元。颜值与拼装手感优异，翼展联动与双头龙变形流畅，热能鞭多段关节表现出色。",
    },
    {
        "product_code": "39",
        "kit_name": "ZGMF-56E2/α 威力型脉冲高达 Spec II",
        "detail": "2024年2月发售，售价3410日元。剧场版脉冲升级版，采用新色调，继承原版脉冲优秀稳定的机械素质。",
    },
    {
        "product_code": "40",
        "kit_name": "RX-78-2 高达 Ver.2.0",
        "detail": "2024年8月发售，售价3850日元。RG新扛把子，全新全拼装内构骨架，隐藏水口+精密刻线，彻底告别初代软骨病。",
    },
    {
        "product_code": "41",
        "kit_name": "ORB-01 拂晓高达（大鹫装备）",
        "detail": "2024年12月发售，售价8800日元。全机金色电镀光彩夺目，但骨架回退沿用部分老一体件，售价偏高。",
    },
    {
        "product_code": "42",
        "kit_name": "GF13-017NJ 闪光高达",
        "detail": "2025年6月发售，售价3850日元。沿用神高达优秀格斗骨架设计，继承顶级可动性，具备超级模式展开变形。",
    },
    {
        "product_code": "43",
        "kit_name": "XXXG-00W0 飞翼零式高达",
        "detail": "2025年9月发售，售价4620日元。W系列30周年纪念作，旋转喷口联动机械设计亮眼，整体素质扎实在线。",
    },
]

with SessionLocal() as session:
    added = 0
    updated = 0
    for item in bandai_rg_list:
        existing = session.scalars(
            select(Product).where(
                Product.manufacturer == "万代",
                Product.product_code == item["product_code"],
            )
        ).first()

        if existing:
            existing.kit_name = item["kit_name"]
            existing.product_line = "RG"
            existing.origin_type = "通贩"
            existing.source = "手动录入"
            existing.detail = item["detail"]
            updated += 1
            print(f"Updated: [{item['product_code']}] {item['kit_name']}")
        else:
            prod = Product(
                id=uuid.uuid4(),
                manufacturer="万代",
                product_code=item["product_code"],
                product_line="RG",
                origin_type="通贩",
                source="手动录入",
                kit_name=item["kit_name"],
                detail=item["detail"],
            )
            session.add(prod)
            added += 1
            print(f"Added:   [{item['product_code']}] {item['kit_name']}")

    session.commit()
    print(f"\nExecution finished! Added: {added}, Updated: {updated}, Total: {len(bandai_rg_list)}")
