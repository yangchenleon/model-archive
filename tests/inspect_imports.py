import csv
from pathlib import Path

imports_dir = Path("imports")
for p in sorted(imports_dir.glob("*.csv")):
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        row = next(reader, None)
        if row:
            print(f"{p.name}: 来源类型='{row.get('来源类型')}', cols={list(row.keys())}")
