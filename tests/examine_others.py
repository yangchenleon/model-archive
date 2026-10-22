import csv
from pathlib import Path

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

targets = ["SUPA", "四海", "GL", "星聚", "神兽", "乐豹", "千叶模型", "海尔兹"]
for t in targets:
    t_rows = [r for r in rows if (r.get("厂家") or "").strip() == t]
    print(f"\n=== {t} ({len(t_rows)} rows) ===")
    for r in t_rows:
        print(f"  {r['日期']:10s} | {r['模型']}")
