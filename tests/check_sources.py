import csv
from pathlib import Path

norm_dir = Path("outputs/normalized/season-4951163")
types = set()
for p in norm_dir.glob("*.csv"):
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            types.add(r.get("来源类型"))
print("Types in outputs/normalized/season-4951163:", types)
