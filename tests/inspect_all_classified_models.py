import csv
from pathlib import Path

OUT_DIR = Path("outputs/classified")

for p in sorted(OUT_DIR.glob("*.csv")):
    if p.name == "其他与小众厂商.csv":
        continue
    print(f"\n==================== {p.name} ====================")
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, 1):
            print(f"[{i:2d}] {r['日期']:10s} | {r['模型']:35s} | 原: {r['原始记录']}")
