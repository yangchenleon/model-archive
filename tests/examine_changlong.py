import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

changlong_rows = [r for r in rows if (r.get("厂家") or "").strip() in ("长龙", "辰龙")]
print(f"Total 长龙 rows: {len(changlong_rows)}")
for r in changlong_rows:
    print(f"  {r['日期']:10s} | {r['厂家']:6s} | {r['模型']}")
