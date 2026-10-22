import csv
from pathlib import Path

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")
for i, r in enumerate(rows, 1):
    print(f"{i:2d} | 厂商: {r['厂商']} | 编号: {r['产品编号']} | 来源: {r['来源类型']} | 产品线: {r['产品线']} | 模型: {r['模型名称']} | 版本: {r['版本/配色']} | 链接: {r['资料来源'].split('/')[-1]}")
