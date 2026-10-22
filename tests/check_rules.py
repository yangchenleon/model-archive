import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Check rules related to 星动 and 独角兽/报丧/菲尼克斯
rules_path = ROOT / "tools" / "normalize_rules.csv"
with open(rules_path, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    print("--- Existing rules matching 爆桑 / 独角 / 报丧 / 星动 ---")
    for r in reader:
        pat = r.get("pattern", "")
        rep = r.get("replacement", "")
        scope = r.get("scope", "")
        if any(k in pat or k in rep or k in scope for k in ["爆桑", "报丧", "星动", "独角", "菲尼克斯", "逍遥", "霜之哀伤"]):
            print(f"[{r.get('rule_type')}] scope={scope} | {pat} -> {rep} ({r.get('note')})")
