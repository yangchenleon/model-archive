import csv
from pathlib import Path
from collections import Counter

csv_path = Path("outputs/classified/其他与小众厂商.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows in 其他与小众厂商: {len(rows)}")

counts = Counter(r["厂家"] for r in rows)
print(f"Total distinct manufacturers in this table: {len(counts)}")
print("\nBreakdown:")
for mfg, c in counts.most_common():
    print(f"  {mfg:18s}: {c} 款")
