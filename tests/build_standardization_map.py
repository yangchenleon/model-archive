import csv
import re
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")

# Let's inspect STAR products specifically
star_rows = []
for r in rows:
    mfg = (r.get("厂家") or "").strip()
    if mfg in ("STAR", "星动") or mfg.startswith("精神力") or mfg.startswith("都不知道"):
        star_rows.append(r)

print(f"Total STAR rows: {len(star_rows)}")
for r in star_rows:
    print(f"  {r['日期']:10s} | {r['模型']}")
