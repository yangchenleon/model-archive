import csv
from pathlib import Path
from collections import Counter

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Standardize manufacturers
def normalize_mfg(raw_mfg: str, raw_model: str) -> tuple[str, str]:
    m = (raw_mfg or "").strip()
    model = (raw_model or "").strip()
    
    # Special rows with syntax errors in raw CSV
    if m.startswith("精神力再版（唯美to"):
        return "STAR", "精神力高达再版（唯美转STAR，不知有无换盒）"
    if m.startswith("都不知道啥时候出了个命运二式"):
        return "STAR", "命运高达二式（最终决战印象配色；错版修正换盒）"
    if m == "FM自由":
        return "未知/待定", f"FM自由高达（{model}）"
    
    # Common mappings
    mapping = {
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
        "海尔兹": "千叶模型", # 海尔兹提坦斯配色即千叶海兹尔
        "星动": "STAR-星动",
        "STAR": "STAR-星动",
    }
    norm_m = mapping.get(m, m)
    if not norm_m:
        norm_m = "未知/待定"
    return norm_m, model

counts = Counter()
for r in rows:
    nm, nmod = normalize_mfg(r.get("厂家"), r.get("模型"))
    counts[nm] += 1

print("Normalized manufacturer counts:")
for m, c in counts.most_common():
    print(f"  {m:18s}: {c}")
