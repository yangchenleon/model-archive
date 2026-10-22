import csv
from pathlib import Path

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")
kits = {}
for i, r in enumerate(rows, 1):
    m = r['模型名称']
    v = r['版本/配色']
    kits.setdefault(m, []).append((i, v, r['产品编号'], r['资料来源'].split('/')[-1]))

for m, variants in kits.items():
    print(f"\n【{m}】({len(variants)} 款):")
    for row_idx, v, code, bv in variants:
        print(f"   [行{row_idx:2d}] 版本: {v:30s} | 编号: {code:8s} | {bv}")
