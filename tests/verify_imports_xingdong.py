import csv
from pathlib import Path

csv_path = Path("imports/星动系.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows in {csv_path}: {len(rows)}")

# Verify required fields
for i, r in enumerate(rows, 1):
    if not r.get("模型名称"):
        print(f"Row {i}: Missing 模型名称")
    if not r.get("资料来源"):
        print(f"Row {i}: Missing 资料来源")

# Summary by model
summary = {}
for r in rows:
    name = r["模型名称"]
    summary.setdefault(name, []).append(r["版本/配色"])

print("\n--- Summary by Model ---")
for name, variants in summary.items():
    print(f"• {name} ({len(variants)} 款): {', '.join(variants)}")
