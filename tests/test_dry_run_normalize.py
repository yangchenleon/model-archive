import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.normalize_products import load_rules, process_season, collect_rows, PROMOTE_MAP, SPLIT_EXCEPTIONS

rules = load_rules(ROOT / "tools" / "normalize_rules.csv")
for rule in rules:
    if rule.rtype == "拆分例外":
        SPLIT_EXCEPTIONS.add(rule.pattern)
    elif rule.rtype == "版本值提升产品":
        PROMOTE_MAP[rule.pattern] = rule

seasons = collect_rows()
rows_4951163 = seasons.get("season-4951163", [])

# Filter for the two new BVs
new_bvs = {"BV1caui68EcR", "BV1cob76FEdG"}
target_rows = [r for r in rows_4951163 if r.get("_bv") in new_bvs]

print(f"Total raw rows collected for new BVs: {len(target_rows)}")
out, split_count, promote_count = process_season(target_rows, rules)
print(f"After normalize: {len(out)} rows (split: {split_count}, promote: {promote_count})")

print("\n--- Normalized rows for BV1caui68EcR ---")
for r in out:
    if r["_bv"] == "BV1caui68EcR":
        print(f"厂商={r['厂商']} | 产品编号={r['产品编号']} | 产品线={r['产品线']} | 模型名称={r['模型名称']} | 版本={r['版本/配色']}")

print("\n--- Normalized rows for BV1cob76FEdG ---")
for r in out:
    if r["_bv"] == "BV1cob76FEdG":
        print(f"厂商={r['厂商']} | 产品编号={r['产品编号']} | 产品线={r['产品线']} | 模型名称={r['模型名称']} | 版本={r['版本/配色']}")
