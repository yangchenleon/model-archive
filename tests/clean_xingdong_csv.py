import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = ROOT / "outputs" / "normalized" / "season-4951163" / "星动系.csv"
DEST_PATH = ROOT / "imports" / "星动系.csv"

FIELDS = ["厂商", "产品编号", "来源类型", "产品线", "模型名称", "版本/配色", "详情", "资料来源"]

with open(SRC_PATH, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    raw_rows = list(reader)

print(f"Original row count: {len(raw_rows)}")

cleaned_rows = []
seen_keys = set()
dedup_count = 0

for i, r in enumerate(raw_rows, 1):
    mfg = (r.get("厂商") or "").strip()
    code = (r.get("产品编号") or "").strip()
    origin = (r.get("来源类型") or "").strip()
    line = (r.get("产品线") or "").strip()
    name = (r.get("模型名称") or "").strip()
    variant = (r.get("版本/配色") or "").strip()
    detail = (r.get("详情") or "").strip()
    source = (r.get("资料来源") or "").strip()

    # 1. 规范化来源类型为 阿兜MODEL视频转写
    if origin in ("视频转写", "阿兜MODEL视频转写", ""):
        origin = "阿兜MODEL视频转写"

    # 2. 清理产品编号：HG / HG TOV 是产品线而非编号，星动全系无独立产品编号
    if code in ("HG", "HG TOV"):
        code = ""

    # 3. 规范化“未详”等无意义版本为“原色”
    if variant == "未详":
        variant = "原色"

    # 4. 去重判断：以 (厂商, 产品编号, 来源类型, 产品线, 模型名称, 版本/配色) 为唯一键
    key = (mfg, code, origin, line, name, variant)
    if key in seen_keys:
        print(f"Found duplicate at original row {i}: {key}")
        dedup_count += 1
        continue
    seen_keys.add(key)

    cleaned_rows.append({
        "厂商": mfg,
        "产品编号": code,
        "来源类型": origin,
        "产品线": line,
        "模型名称": name,
        "版本/配色": variant,
        "详情": detail,
        "资料来源": source,
    })

print(f"Cleaned row count: {len(cleaned_rows)} (Deduplicated: {dedup_count})")

# Write to imports/星动系.csv
with open(DEST_PATH, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(cleaned_rows)

print(f"Successfully wrote {len(cleaned_rows)} rows to {DEST_PATH}")
