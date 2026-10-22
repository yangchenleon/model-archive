import csv
from pathlib import Path

rules_path = Path("tools/normalize_rules.csv")
with open(rules_path, "r", encoding="utf-8-sig") as f:
    rules = list(csv.DictReader(f))

print(f"Total rules: {len(rules)}")
by_type = {}
for r in rules:
    by_type.setdefault(r["rule_type"], []).append(r)

for t, rlist in by_type.items():
    print(f"\n=== {t} ({len(rlist)} rules) ===")
    for r in rlist[:10]:
        print(f"  [{r['scope']}] {r['field']}: '{r['pattern']}' -> '{r['replacement']}' ({r.get('note')})")
    if len(rlist) > 10:
        print(f"  ... and {len(rlist) - 10} more")
