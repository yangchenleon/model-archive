import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "outputs" / "timeline_raw.csv"
OUT_DIR = ROOT / "outputs" / "classified"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(RAW_CSV, "r", encoding="utf-8-sig") as f:
    raw_rows = list(csv.DictReader(f))

# 1. 厂商标准化映射
def normalize_mfg(raw_mfg: str, raw_model: str) -> tuple[str, str]:
    m = (raw_mfg or "").strip()
    mod = (raw_model or "").strip()
    
    # 修复CSV逗号错位或特殊标注
    if m.startswith("精神力再版（唯美to"):
        return "STAR-星动", "精神力高达再版（唯美转STAR，不知有无换盒）"
    if m.startswith("都不知道啥时候出了个命运二式"):
        return "STAR-星动", "命运高达二式（最终决战印象配色；错版修正换盒）"
    if m == "FM自由":
        return "待确认/未知", f"FM自由高达（{mod}）"
    
    mfg_map = {
        "STAR": "STAR-星动",
        "星动": "STAR-星动",
        "辰龙": "长龙",
        "虎兽": "兽虎模型",
        "JMS": "集模社",
        "XFS": "星锋社",
        "财喵喵": "农场主",
        "胖虎": "胖虎模型",
        "猛虎": "猛虎模型",
        "爆爆": "爆爆模型",
        "合模线": "摩动核",
        "二师弟": "俺猪二师弟",
        "巨匠": "聚匠模型",
        "海尔兹": "千叶模型",
        "乐豹": "乐豹模型",
        "星聚": "星聚模型",
        "神兽": "神兽模型",
    }
    norm_m = mfg_map.get(m, m)
    if not norm_m:
        norm_m = "待确认/未知"
    return norm_m, mod

# 2. 模型名称标准化规则
def standardize_model(mfg: str, raw_model: str) -> str:
    s = raw_model.strip()
    if not s:
        return "未注明机体"
        
    # 通用错别字与音译修正
    s = s.replace("钣喷", "板喷")
    s = s.replace("海尔兹", "海兹尔")
    s = s.replace("元组", "元祖")
    s = s.replace("大版", "大阪")
    s = s.replace("风铃", "风灵")
    s = s.replace("sd", "SD").replace("Sd", "SD")
    s = s.replace("rg", "RG").replace("Rg", "RG")
    s = s.replace("mg", "MG").replace("Mg", "MG")
    s = s.replace("hg", "HG").replace("Hg", "HG")
    s = s.replace("fm", "FM").replace("Fm", "FM")
    s = re.sub(r"\bqux\b|\bgqux\b|\bGqux\b", "GQX", s, flags=re.IGNORECASE)
    s = s.replace("1：25", "1/25")
    s = s.replace("爆桑女妖", "报丧女妖").replace("暴丧女妖", "报丧女妖")
    s = s.replace("月渎", "月读")

    # 沙扎比系列
    if s == "沙扎比-原版":
        return "沙扎比（原版/原色）"
    if s in ("沙扎比", "沙"):
        return "沙扎比"
    if s == "白沙":
        return "沙扎比（白色版）"
    if s == "白沙（白灰双色板件）":
        return "沙扎比（白沙/白灰双色板件）"
    if s == "电镀沙":
        return "沙扎比（电镀版）"
    if s in ("彩透沙", "彩透沙扎比"):
        return "沙扎比（彩透版）"
    if s in ("彩透电镀沙扎比", "沙扎比彩透电镀"):
        return "沙扎比（彩透电镀版）"
    if s == "幻彩沙扎比":
        return "沙扎比（幻彩版）"
    if s == "爱马仕橙沙扎比":
        return "沙扎比（爱马仕橙）"
    if s == "樱花粉沙扎比":
        return "沙扎比（樱花粉）"
    if s == "黑色沙扎比":
        return "沙扎比（黑色版）"
    if s == "青花瓷沙扎比":
        return "沙扎比（青花瓷版）"
    if s.startswith("机械电镀透明银") and "沙扎比" in s:
        return "沙扎比（机械电镀透明银版，之前是无电镀）"
    if s.startswith("机械透明") and "沙扎比" in s:
        return "沙扎比（机械透明RG版）"
    if s.startswith("手工电镀") and "沙扎比" in s:
        return "沙扎比（手工电镀/板喷版）"
    if s.startswith("1/96") and "沙扎比" in s:
        return "沙扎比（1/96放大RG版）"
    if s == "GK沙扎比":
        return "沙扎比（GK造型版）"
    if s == "福冈沙":
        return "福冈沙扎比"
    if s == "RG福冈沙":
        return "福冈沙扎比（RG版）"
    if s == "福冈沙-彩透电镀":
        return "福冈沙扎比（彩透电镀版）"
    if s == "跟进彩透电镀福冈沙":
        return "福冈沙扎比（彩透电镀版跟进）"
    if s.startswith("跟进（盒子很劣质"):
        return "福冈沙扎比配件包（跟进劣质盒版）"
    if s == "福冈沙蟹钳配件包":
        return "福冈沙扎比蟹钳配件包"
    if s == "福冈沙蟹钳-彩透电镀配件包":
        return "福冈沙扎比蟹钳配件包（彩透电镀版）"

    # 厂家特定机型归纳
    if mfg == "四海":
        if s == "半磨砂透":
            return "沙扎比（半磨砂透版）"
        if s == "电镀蓝":
            return "沙扎比（电镀蓝版）"
        if s == "电镀金":
            return "沙扎比（电镀金版）"
        if s == "福冈黑":
            return "福冈沙扎比（黑金版）"

    if mfg == "千叶模型" and s == "提坦斯配色":
        return "海兹尔（提坦斯配色）"

    if mfg == "乐豹模型":
        if s in ("GQX红", "GQX 红"):
            return "GQX（红色款）"
        if s in ("gqx消光更新版", "GQX消光更新版"):
            return "GQX（消光更新版）"
        if "加农" in s:
            sub = s.replace("gqx", "").replace("qux", "").replace("GQX", "").replace("加农", "").replace("-", "").strip()
            return f"GQX加农（{sub}）"

    if mfg == "GL":
        if s == "高战蟹-红色":
            return "高战蟹（红色款）"
        if s.startswith("风灵"):
            return "风灵高达（暗黑未启动色、白紫配色）"
        if s.startswith("SD风灵"):
            return "SD风灵高达（带特效件）"
        if "大白鹅" in s:
            return "佩涅罗佩/大白鹅（黑色板喷）"
        if s == "RG海牛":
            return "RG海牛高达"

    if mfg == "长龙":
        if s.lower().startswith("mgex独角兽"):
            return "MGEX独角兽（蓝牙灯组）"
        if s == "无灯三套骨架合一":
            return "独角兽（无灯三套骨架合一）"
        if s == "修复版换色-黑":
            return "修复版换色-黑"
        if s == "钛镀":
            return "钛镀版（机体待定）"
        if s == "RG海牛":
            return "RG海牛高达"
        if s == "RG海牛电镀":
            return "RG海牛高达（电镀版）"

    # 独角兽与女妖/凤凰系列
    if s == "全装独角兽再版-红":
        return "全装备独角兽（红骨再版）"
    if s == "全装独角兽-红消光再版":
        return "全装备独角兽（红骨消光再版）"
    if s.startswith("独角模式独角兽"):
        return "独角兽（独角模式板喷）"
    if s == "红独角电镀":
        return "独角兽（红骨电镀版）"
    if s == "黄金独角兽x2":
        return "独角兽（黄金电镀双子星）"
    if s in ("完美神圣独角兽", "神圣独角兽"):
        return "完美独角兽（神圣版）"
    if s == "觉醒绿":
        return "独角兽（觉醒绿）"
    if s == "暗钢配色":
        return "独角兽（暗钢配色）"
    if s == "透明结晶":
        return "结晶独角兽（透明版）"
    if s == "紫结晶":
        return "结晶独角兽（暗紫版）"
    if s == "HG结晶再版":
        return "结晶独角兽（HG再版）"
    if s == "报丧女妖消光再版":
        return "报丧女妖（消光再版）"
    if s == "彩透女妖":
        return "报丧女妖（彩透版）"
    if s == "报丧板喷":
        return "报丧女妖（板喷版）"
    if s == "棱镜报丧x2":
        return "报丧女妖（棱镜蓝x2）"
    if s == "报丧女妖二号机":
        return "报丧女妖二号机"
    if s == "女神":
        return "报丧女妖命运女神（原色）"
    if s == "命运女神消光":
        return "报丧女妖命运女神（消光版）"
    if s == "黑女神":
        return "报丧女妖命运女神（黑色版）"
    if s == "黑凤凰":
        return "菲尼克斯NT（电镀黑）"
    if s == "粉色凤凰":
        return "菲尼克斯NT（电镀粉）"
    if s == "独角模式凤凰再版":
        return "菲尼克斯（独角模式电镀再版）"

    # 京宝梵
    if s.startswith("电镀京宝梵"):
        return s.replace("电镀京宝梵", "京宝梵（电镀版）")
    if s == "惊异京宝梵":
        return "京宝梵（惊异款）"
    if s == "白色京宝梵":
        return "京宝梵（白色款）"

    # 老虎
    if s.startswith("老虎-白色领袖"):
        return "老虎（白色领袖款）"
    if s == "创制R35老虎":
        return "老虎（创制R35款）"
    if s == "暗夜领袖B3老虎再版":
        return "老虎B3特装型（暗夜领袖款再版）"
    if s == "新生老虎":
        return "新生老虎"
    if s == "老虎特装型再版":
        return "老虎特装型（再版）"
    if s.startswith("gto拉老虎原型"):
        return "GTO老虎原型机（再版）"

    # 元祖
    if s in ("大版世博元祖樱花粉", "大阪世博元祖樱花粉"):
        return "元祖RX-78-2（大阪世博樱花粉限定）"
    if s == "大阪限定世博元祖":
        return "元祖RX-78-2（大阪世博限定）"
    if s.startswith("RG元组九龙"):
        return "元祖RX-78-2（RG九龙拳一&世博配件包）"
    if s == "RG元祖-初音":
        return "元祖RX-78-2（RG初音未来配色）"
    if s == "RG元祖-彩透":
        return "元祖RX-78-2（RG彩透版）"
    if s.startswith("RG元祖 原色2.0"):
        return "元祖RX-78-2（RG 2.0原色版）"
    if s == "G3配色" and mfg == "高高":
        return "元祖RX-78-2（RG 2.0 G3配色）"
    if s == "九龙拳一元祖":
        return "元祖RX-78-2（九龙拳一配色）"
    if s == "元祖再版":
        return "元祖RX-78-2（再版）"
    if s == "元祖2.0":
        return "元祖RX-78-2（2.0版）"
    if s == "元祖":
        return "元祖RX-78-2"

    # 牛高达
    if s == "福冈牛":
        return "牛高达（福冈实物大样式）"
    if s == "RG福冈牛":
        return "牛高达（RG福冈限定）"
    if s == "GK福冈牛":
        return "牛高达（GK福冈样式）"
    if s == "GK牛":
        return "牛高达（GK造型版）"
    if s == "rg钛镀牛":
        return "牛高达（RG钛白电镀版）"
    if s == "重牛":
        return "重装牛高达（HWS形态）"
    if s == "重牛配件包":
        return "重装牛高达HWS装备配件包"
    # 巴尔基尔
    if s == "巴尔基尔":
        return "巴尔基尔"
    if s == "红巴尔基尔":
        return "巴尔基尔（红色款）"
    if s == "巴尔基尔-红":
        return "巴尔基尔（红色款）"

    # 飞翼
    if s == "飞翼":
        return "飞翼高达"
    if s == "樱花飞翼":
        return "飞翼高达（樱花粉配色）"
    if s in ("飞翼蓝白渐变", "蓝白渐变飞翼"):
        return "飞翼高达（蓝白渐变配色）"
    if s == "电镀紫MGSD飞翼":
        return "MGSD飞翼高达（电镀紫配色）"
    if s == "MGSE鲁路修配色MGSD飞翼":
        return "MGSD飞翼高达（鲁路修特别配色）"
    if s == "RG零式飞翼":
        return "飞翼零式EW（RG版）"
    if s == "卡板飞翼":
        return "飞翼零式EW（Ka版）"

    # 自由 / 强袭自由
    if s == "MGSG樱花自由修复":
        return "MGSD自由高达（樱花粉修复版）"
    if s == "MGEX透明外甲强袭自由":
        return "MGEX强袭自由（透明外甲版）"
    if s == "完美强袭自由":
        return "完美强袭自由高达"
    if s == "新生强袭自由改":
        return "新生强袭自由高达改"
    if s == "MGEX白强袭":
        return "MGEX强袭高达（纯白配色）"
    if s == "暮光白MGEX":
        return "MGEX强袭高达（暮光白配色）"
    if s == "MGEX强袭修复版":
        return "MGEX强袭高达（修复版）"
    if s == "彩透非凡强袭自由":
        return "全能强袭自由高达（彩透版）"

    # 命运
    if s == "新生命运":
        return "新生命运高达"
    if s == "最终决战命运":
        return "命运高达（最终决战样式）"
    if s == "海涅命运":
        return "命运高达（海涅专用机）"
    if s.startswith("命运-彩透") or s.startswith("彩透命运"):
        return "命运高达（彩透版）"
    if s.startswith("命运二式单体"):
        return "命运高达二式（单机错版修正换盒）"
    if s.startswith("宙斯魅影二式"):
        return "命运高达二式&宙斯魅影（更新大光翼）"
    if s.startswith("宙斯（不带/带命运）"):
        return "宙斯魅影装备（单体/带命运高达套装）"
    if s == "海涅+宙斯":
        return "命运高达（海涅机&宙斯魅影装备）"

    # 巴巴托斯
    if s == "mgsd巴巴托斯":
        return "MGSD巴巴托斯"
    if s == "巴巴托斯玄武修复":
        return "巴巴托斯（玄武配色修复版）"
    if s == "MGSD修复 原色 玄武色":
        return "MGSD巴巴托斯（修复原色/玄武色）"
    if s == "MGSD巴巴托斯帝王":
        return "MGSD巴巴托斯天狼座帝王形态"
    if s == "HG巴巴托斯第四形态":
        return "HG巴巴托斯（第四形态）"
    if s == "巴巴托斯第四形态":
        return "巴巴托斯（第四形态）"
    if s == "MG巴巴托斯-第四形态":
        return "MG巴巴托斯（第四形态）"
    if s.startswith("惊异巴巴托斯"):
        return "惊异巴巴托斯（板喷版）"
    if s.startswith("普通惊异巴巴托斯"):
        return "惊异巴巴托斯（普通版）"
    if s.startswith("巴巴托斯配件包"):
        return "巴巴托斯配件包（双战锤/战锤+大刀）"
    if s == "巴巴托斯胸像":
        return "巴巴托斯胸像"

    # 扎古
    if s == "扎古灰再版":
        return "扎古（灰色款再版）"
    if s.startswith("扎古绿再版"):
        return "扎古（绿色消光再版）"
    if s == "琉璃扎古":
        return "扎古（琉璃色版）"
    if s == "扎古修复（妈的）":
        return "扎古（修复版，原注吐槽）"
    if s == "扎古I黑+绿再版消光":
        return "扎古I（黑+绿消光再版）"
    if s == "安魂曲扎古-索拉里":
        return "扎古II（复仇的安魂曲·索拉里专用机）"
    if s == "安魂曲扎古2型":
        return "扎古II F型（复仇的安魂曲样式）"

    # 叙述高达
    if s == "彩透叙述C装":
        return "叙述高达C装备（彩透版）"
    if s == "彩透A装备":
        return "叙述高达A装备（彩透版）"
    if s == "A装备":
        return "叙述高达A装备"
    if s == "叙述B":
        return "叙述高达B装备"
    if s == "卡叙述":
        return "叙述高达（Ka版）"
    if s == "板喷叙述":
        return "叙述高达（板喷版）"

    return s

# 解析并整理所有行
processed = []
for r in raw_rows:
    raw_d = (r.get("日期") or "").strip()
    raw_m = (r.get("厂家") or "").strip()
    raw_k = (r.get("模型") or "").strip()
    
    norm_m, raw_k = normalize_mfg(raw_m, raw_k)
    norm_k = standardize_model(norm_m, raw_k)
    
    # 解析日期便于排序（2026/5/22 -> datetime）
    try:
        dt = datetime.strptime(raw_d, "%Y/%m/%d")
    except Exception:
        dt = datetime(1970, 1, 1)
        
    processed.append({
        "日期": raw_d,
        "厂家": norm_m,
        "模型": norm_k,
        "原始记录": raw_k,
        "_dt": dt,
        "_raw_mfg": raw_m,
    })

# 3. 统计各厂商数量，决定独立表名单
MAJOR_MFGS = ["STAR-星动", "高高", "长龙", "SUPA", "四海", "GL", "星聚模型", "千叶模型", "神兽模型", "乐豹模型"]

groups = defaultdict(list)
for item in processed:
    m = item["厂家"]
    if m in MAJOR_MFGS:
        groups[m].append(item)
    else:
        groups["其他与小众厂商"].append(item)

# 4. 排序规则：
# 独立大厂表：按标准化模型名称排序（同机型版本归集），同模型按日期倒序
# 其他小众厂商表：按厂家拼音/字母排序 -> 标准化模型名称 -> 日期倒序
FIELDS = ["日期", "厂家", "模型", "原始记录"]

print(f"\nWriting files to {OUT_DIR}:")
for gname, items in groups.items():
    if gname == "其他与小众厂商":
        # 排序：厂家 -> 模型 -> 日期倒序
        items.sort(key=lambda x: (x["厂家"], x["模型"], -x["_dt"].timestamp()))
    else:
        # 排序：模型 -> 日期倒序
        items.sort(key=lambda x: (x["模型"], -x["_dt"].timestamp()))
        
    filename = f"{gname}.csv"
    out_file = OUT_DIR / filename
    with open(out_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
    print(f"  ✓ {filename:22s}: {len(items):3d} 条记录")

print("\nDone!")
