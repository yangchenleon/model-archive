import csv
from pathlib import Path

csv_path = Path("outputs/classified/STAR-星动.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")
for i, r in enumerate(rows, 1):
    print(f"[{i:2d}] {r['日期']:10s} | {r['模型']:32s} | 原: {r['原始记录']}")
