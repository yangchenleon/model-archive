import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for i in range(100, min(225, len(rows))):
    r = rows[i]
    print(f"[{i+1:3d}] {r['日期']:10s} | {r['厂家']:15s} | {r['模型']}")
