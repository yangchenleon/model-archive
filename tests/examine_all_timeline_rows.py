import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

print(f"Total rows: {len(rows)}")

# Let's inspect empty manufacturer rows
print("\n=== Rows with empty 厂家 ===")
for i, r in enumerate(rows, 1):
    if not (r.get("厂家") or "").strip():
        print(f"Row {i:3d}: 日期={r.get('日期')} | 厂家='{r.get('厂家')}' | 模型='{r.get('模型')}'")

# Let's inspect empty model rows
print("\n=== Rows with empty 模型 ===")
for i, r in enumerate(rows, 1):
    if not (r.get("模型") or "").strip():
        print(f"Row {i:3d}: 日期={r.get('日期')} | 厂家='{r.get('厂家')}' | 模型='{r.get('模型')}'")

# Let's inspect unusual manufacturers (contains punctuation or words)
print("\n=== Unusual 厂家 ===")
for i, r in enumerate(rows, 1):
    mfg = (r.get("厂家") or "").strip()
    if any(c in mfg for c in ["（", "，", "/", " "]) or len(mfg) > 8:
        print(f"Row {i:3d}: 日期={r.get('日期')} | 厂家='{mfg}' | 模型='{r.get('模型')}'")
