import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

gaogao_rows = [r for r in rows if (r.get("厂家") or "").strip() == "高高"]
print(f"Total 高高 rows: {len(gaogao_rows)}")
for r in gaogao_rows:
    print(f"  {r['日期']:10s} | {r['模型']}")
