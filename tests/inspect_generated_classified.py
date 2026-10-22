import csv
from pathlib import Path

OUT_DIR = Path("outputs/classified")

for p in sorted(OUT_DIR.glob("*.csv")):
    print(f"\n==================== {p.name} ====================")
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"Total rows: {len(rows)}")
        for i, r in enumerate(rows[:8], 1):
            print(f"  [{i:2d}] {r['日期']:10s} | {r['厂家']:10s} | {r['模型']:32s} | 原: {r['原始记录']}")
        if len(rows) > 8:
            print(f"  ... and {len(rows) - 8} more rows")
