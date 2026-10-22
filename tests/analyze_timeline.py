import csv
from pathlib import Path
from collections import Counter

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows: {len(rows)}")

mfg_counts = Counter((r.get("厂家") or "").strip() for r in rows)
print(f"Total distinct manufacturers: {len(mfg_counts)}")
print("\n--- Manufacturer Counts (descending) ---")
for mfg, count in mfg_counts.most_common():
    print(f"{mfg or '[空白]':25s}: {count}")
