import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")

# Let's inspect model names with notes, brackets, commas, or typos
for i, r in enumerate(rows, 1):
    m = (r.get("模型") or "").strip()
    mfg = (r.get("厂家") or "").strip()
    date = (r.get("日期") or "").strip()
    if any(c in m for c in ["（", "(", "【", "、", "；", "&", "+", "修复", "再版", "电镀", "彩透", "放大", "钛镀", "消光", "换色", "RG", "MG", "HG", "SD", "FM"]):
        pass # very common
    print(f"[{i:3d}] {date:10s} | {mfg:15s} | {m}")
