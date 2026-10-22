import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.normalize_products import (
    load_rules,
    collect_rows,
    process_season,
    PROMOTE_MAP,
    SPLIT_EXCEPTIONS,
    Rule,
)
from tests.test_smart_split import smart_split_versions

# Monkey patch smart_split_versions into normalize_products
import tools.normalize_products as np_mod
np_mod.split_versions = smart_split_versions

rules = load_rules(ROOT / "tools" / "normalize_rules.csv")

# Add new candidate rules
candidate_rules = [
    Rule("厂商映射", "BV:BV1caui68EcR", "厂商", "ACE HG", "ACE", "分P中厂商为ACE；HG为产品线"),
    Rule("产品线映射", "BV:BV1caui68EcR", "产品线", "1/1", "1/100", "DA神意高达为1/100比例"),
    Rule("版本值词替换", "BV:BV1caui68EcR", "版本/配色", "双之哀伤", "霜之哀伤", "RC夜莺霜之哀伤涂装"),
    Rule("详情词替换", "BV:BV1caui68EcR", "详情", "JK", "GK", "GK改拼装音译修正"),
    Rule("详情词替换", "BV:BV1caui68EcR", "详情", "神一", "神意", "神意高达音译修正"),
    Rule("版本值词替换", "BV:BV1cob76FEdG", "版本/配色", "红谷", "红骨", "红骨独角兽音译修正"),
    Rule("版本值词替换", "BV:BV1cob76FEdG", "版本/配色", "绿谷", "绿骨", "绿骨独角兽音译修正"),
    Rule("版本值词替换", "BV:BV1cob76FEdG", "版本/配色", "爆桑女妖", "报丧女妖", "报丧女妖音译修正"),
]
rules.extend(candidate_rules)

for rule in rules:
    if rule.rtype == "拆分例外":
        SPLIT_EXCEPTIONS.add(rule.pattern)
    elif rule.rtype == "版本值提升产品":
        PROMOTE_MAP[rule.pattern] = rule

seasons = collect_rows()
rows = seasons.get("season-4951163", [])
target_rows = [r for r in rows if r.get("_bv") in {"BV1caui68EcR", "BV1cob76FEdG"}]

out, split_count, promote_count = process_season(target_rows, rules)

print(f"Processed {len(target_rows)} rows -> {len(out)} rows (splits: {split_count})")
print("\n=== BV1caui68EcR Normalized ===")
for r in out:
    if r["_bv"] == "BV1caui68EcR":
        print(f"[{r['厂商']}] [{r['产品线']}] {r['模型名称']} | 版本: {r['版本/配色']}")
        print(f"   详情: {r['详情'][:60]}...")

print("\n=== BV1cob76FEdG Normalized ===")
for r in out:
    if r["_bv"] == "BV1cob76FEdG":
        print(f"[{r['厂商']}] [{r['产品线']}] {r['模型名称']} | 版本: {r['版本/配色']}")
