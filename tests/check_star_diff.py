import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RAW_CSV = ROOT / "outputs" / "timeline_raw.csv"

with open(RAW_CSV, "r", encoding="utf-8-sig") as f:
    raw_rows = list(csv.DictReader(f))

# Let's count how many raw rows have STAR or 星动
star_count = 0
for i, r in enumerate(raw_rows, 1):
    m = (r.get("厂家") or "").strip()
    if m in ("STAR", "星动") or m.startswith("精神力") or m.startswith("都不知道"):
        star_count += 1

print(f"Raw rows with STAR or 星动: {star_count}")

# Now let's check what STAR-星动.csv has
with open(ROOT / "outputs" / "classified" / "STAR-星动.csv", "r", encoding="utf-8-sig") as f:
    csv_rows = list(csv.DictReader(f))

print(f"STAR-星动.csv rows: {len(csv_rows)}")

# Which ones in raw are not in STAR-星动.csv?
raw_dates_mods = []
for r in raw_rows:
    m = (r.get("厂家") or "").strip()
    if m in ("STAR", "星动") or m.startswith("精神力") or m.startswith("都不知道"):
        raw_dates_mods.append((r["日期"].strip(), r["模型"].strip()))

csv_raw_records = [(r["日期"].strip(), r["原始记录"].strip()) for r in csv_rows]

print(f"raw_dates_mods length: {len(raw_dates_mods)}")
print(f"csv_raw_records length: {len(csv_raw_records)}")

missing = [x for x in raw_dates_mods if x not in csv_raw_records]
print(f"Missing ({len(missing)}):")
for x in missing:
    print(f"  {x}")
