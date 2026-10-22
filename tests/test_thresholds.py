import csv
from pathlib import Path
from collections import Counter

csv_path = Path("outputs/timeline_raw.csv")
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

# Let's test manufacturer normalization mappings
mfg_map = {
    "辰龙": "长龙",
    "虎兽": "兽虎模型",
    "JMS": "集模社",
    "XFS": "星锋社",
    "财喵喵": "农场主",
    "胖虎": "胖虎模型",
    "爆爆": "爆爆模型",
    "合模线": "摩动核",
    "二师弟": "俺猪二师弟",
}

mapped_counts = Counter()
for r in rows:
    m = (r.get("厂家") or "").strip()
    m = mfg_map.get(m, m)
    mapped_counts[m] += 1

print("--- Threshold >= 5 ---")
major_5 = {m: c for m, c in mapped_counts.items() if c >= 5 and m}
other_5_count = sum(c for m, c in mapped_counts.items() if (c < 5 or not m))
for m, c in sorted(major_5.items(), key=lambda x: -x[1]):
    print(f"  {m:15s}: {c}")
print(f"  [其他厂商汇总]  : {other_5_count}")

print("\n--- Threshold >= 4 ---")
major_4 = {m: c for m, c in mapped_counts.items() if c >= 4 and m}
other_4_count = sum(c for m, c in mapped_counts.items() if (c < 4 or not m))
for m, c in sorted(major_4.items(), key=lambda x: -x[1]):
    print(f"  {m:15s}: {c}")
print(f"  [其他厂商汇总]  : {other_4_count}")
