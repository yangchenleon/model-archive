import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Check all existing outputs/normalized CSVs to see how parentheses are handled
for p in (ROOT / "outputs" / "normalized" / "season-4951163").glob("*.csv"):
    with open(p, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            v = r.get("版本/配色", "")
            if "（" in v or "(" in v:
                if not ("）" in v or ")" in v):
                    print(f"Unbalanced in {p.name}: {v}")
                elif any(sep in v for sep in "、，,"):
                    print(f"Contains comma in {p.name}: {v}")
