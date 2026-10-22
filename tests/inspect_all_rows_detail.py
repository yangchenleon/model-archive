import csv
from pathlib import Path

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")
for i, r in enumerate(rows, 1):
    print(f"--- Row {i:2d} ---")
    print(f"厂商: {r.get('厂商')}")
    print(f"产品编号: {r.get('产品编号')}")
    print(f"来源类型: {r.get('来源类型')}")
    print(f"产品线: {r.get('产品线')}")
    print(f"模型名称: {r.get('模型名称')}")
    print(f"版本/配色: {r.get('版本/配色')}")
    print(f"详情: {r.get('详情')}")
    print(f"资料来源: {r.get('资料来源')}")
