import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "outputs" / "timeline_raw.csv"

with open(RAW_CSV, "r", encoding="utf-8-sig") as f:
    raw_rows = list(csv.DictReader(f))

# Let's inspect where the 80 STAR rows went
from tests.process_and_classify_timeline import normalize_mfg

destinations = Counter()
for r in raw_rows:
    raw_m = (r.get("厂家") or "").strip()
    raw_k = (r.get("模型") or "").strip()
    norm_m, k = normalize_mfg(raw_m, raw_k)
    if "STAR" in raw_m or "星动" in raw_m:
        destinations[norm_m] += 1
        if norm_m != "STAR-星动":
            print("Not STAR-星动:", raw_m, raw_k, "->", norm_m)

print("STAR raw rows mapped to:", destinations)
