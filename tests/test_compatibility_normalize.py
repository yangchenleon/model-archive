import csv
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

import sys
sys.path.insert(0, str(ROOT))

from tools.normalize_products import load_rules, process_season, collect_rows, PROMOTE_MAP, SPLIT_EXCEPTIONS, split_versions
from tests.test_smart_split import smart_split_versions

# Test on all existing rows across all seasons
seasons = collect_rows()
diff_count = 0
for s_name, rows in seasons.items():
    for r in rows:
        bv = r.get("_bv")
        if bv in {"BV1caui68EcR", "BV1cob76FEdG"}:
            continue
        v = r.get("版本/配色", "")
        if v:
            old_res = split_versions(v)
            new_res = smart_split_versions(v)
            if old_res != new_res:
                print(f"Diff in {s_name} {bv}:")
                print(f"  Orig: {v}")
                print(f"  Old : {old_res}")
                print(f"  New : {new_res}")
                diff_count += 1

print(f"Total diffs in historical data: {diff_count}")
