import csv
from pathlib import Path

norm_file = Path("outputs/normalized/season-4951163/星动系.csv")
with open(norm_file, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Rows 21 to {len(rows)}:")
for i in range(20, len(rows)):
    r = rows[i]
    print(f"[{i+1:2d}] 模型: {r['模型名称']:16s} | 版本: {r['版本/配色']:28s} | 详情: {r['详情'][:35]}...")
