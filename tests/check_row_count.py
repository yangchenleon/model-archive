import csv
from pathlib import Path

CLASSIFIED_DIR = Path("outputs/classified")
total = 0
for p in sorted(CLASSIFIED_DIR.glob("*.csv")):
    with open(p, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))[1:]
        print(f"{p.name:25s}: {len(rows)}")
        total += len(rows)
print("Total rows across CSVs:", total)
