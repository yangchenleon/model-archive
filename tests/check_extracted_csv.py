import csv
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_BVS = ["BV1caui68EcR", "BV1cob76FEdG"]

for bv in TARGET_BVS:
    csv_files = glob.glob(str(ROOT / "outputs" / "season-4951163" / "videos" / bv / "csv" / "*.csv"))
    print(f"\n==================== BV: {bv} ====================")
    for p in csv_files:
        print(f"File: {p}")
        with open(p, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            print(f"Row count: {len(rows)}")
            for i, r in enumerate(rows, 1):
                print(f"  [{i}] 厂商={r.get('厂商')} | 编号={r.get('产品编号')} | 产品线={r.get('产品线')} | 模型={r.get('模型名称')} | 版本={r.get('版本/配色')}")
                desc = r.get('详情', '')
                print(f"      详情: {desc[:80]}...")
