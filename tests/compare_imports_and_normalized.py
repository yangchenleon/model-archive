import csv
from pathlib import Path

imports_file = Path("imports/星动系.csv")
norm_file = Path("outputs/normalized/season-4951163/星动系.csv")

with open(imports_file, "r", encoding="utf-8-sig") as f:
    imports_rows = list(csv.DictReader(f))

with open(norm_file, "r", encoding="utf-8-sig") as f:
    norm_rows = list(csv.DictReader(f))

print(f"imports/星动系.csv rows: {len(imports_rows)}")
print(f"outputs/normalized/.../星动系.csv rows: {len(norm_rows)}")

# Let's inspect the first 21 rows in both
for i in range(min(len(imports_rows), len(norm_rows))):
    r_imp = imports_rows[i]
    r_norm = norm_rows[i]
    diffs = {}
    for k in r_imp:
        if r_imp.get(k) != r_norm.get(k):
            diffs[k] = (r_imp.get(k), r_norm.get(k))
    if diffs:
        print(f"\nRow {i+1} diffs:")
        for k, (v1, v2) in diffs.items():
            print(f"  {k}: [imports] '{v1}' vs [norm] '{v2}'")
