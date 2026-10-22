import csv
from pathlib import Path

imports_dir = Path("imports")
for p in sorted(imports_dir.glob("*.csv")):
    if p.name == "products_export.csv":
        continue
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        codes = set()
        for r in reader:
            c = (r.get("产品编号") or "").strip()
            if c:
                codes.add(c)
        sample = list(codes)[:5]
        print(f"{p.stem:20s}: total non-empty codes={len(codes)}, sample={sample}")
