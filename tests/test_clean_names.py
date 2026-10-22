import re
import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

def clean_model_name(raw: str) -> tuple[str, str]:
    """
    Returns (standardized_model, notes)
    standardized_model: used for sorting and clean display
    notes: any remarks, original details, or extracted info
    """
    s = raw.strip()
    if not s:
        return "未注明机体", ""
    
    # Common text fixes
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
    s = s.replace("gqx", "GQX").replace("qux", "GQX").replace("Gqux", "GQX")
    s = s.replace("1：25", "1/25")
    
    # Check if ends with or starts with 沙扎比
    if s in ("沙", "沙扎比"):
        return "沙扎比", ""
    if s == "电镀沙":
        return "沙扎比（电镀版）", ""
    if s == "白沙":
        return "沙扎比（白色版）", ""
    if s == "福冈沙":
        return "福冈沙扎比", ""
    if s == "彩透沙":
        return "沙扎比（彩透版）", ""
        
    return s, ""

print("Sample cleaned names:")
for r in rows[:30]:
    c, note = clean_model_name(r['模型'])
    print(f"Original: {r['模型']:40s} -> Clean: {c}")
