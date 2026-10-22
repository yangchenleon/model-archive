import csv
from pathlib import Path

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

lines = {r['产品线'] for r in rows}
print("Unique 产品线:", lines)
