import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NORM_DIR = ROOT / "outputs" / "normalized" / "season-4951163"

for name in ["早期领先KO盘点.csv", "星动系.csv"]:
    p = NORM_DIR / name
    print(f"\n==================== {name} ({p.stat().st_size} bytes) ====================")
    with open(p, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"Total rows: {len(rows)}")
        for i, r in enumerate(rows, 1):
            bv = r.get("资料来源", "").split("/")[-1]
            print(f"[{i:2d}] {r['厂商']} | {r['产品编号']} | {r['产品线']} | {r['模型名称']} | {r['版本/配色']} | {bv}")
