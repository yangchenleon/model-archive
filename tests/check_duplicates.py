import csv
from pathlib import Path
from collections import Counter

csv_path = Path("outputs/normalized/season-4951163/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Check duplicates by (模型名称, 版本/配色)
counter = Counter()
for i, r in enumerate(rows, 1):
    key = (r['模型名称'], r['版本/配色'])
    counter[key] += 1

print("Duplicates in (模型名称, 版本/配色):")
for k, count in counter.items():
    if count > 1:
        print(f"  {k}: count={count}")
        # print which rows
        for i, r in enumerate(rows, 1):
            if (r['模型名称'], r['版本/配色']) == k:
                print(f"    Row {i}: 编号='{r['产品编号']}', 详情='{r['详情'][:30]}...', 链接='{r['资料来源']}'")
