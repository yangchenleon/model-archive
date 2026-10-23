"""V3 alignment: exact-match grouping only.

Identity is `(normalized brand, normalized product name)` and nothing else — no
similarity, no prefix rules, no variant splitting. Mentions that differ by a
single character become separate products on purpose; the review file lists
look-alike pairs for later alias work.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

PUNCT = re.compile(r"[\s\-_/·・,，。.、()（）\[\]【】:：;；!！?？'\"“”‘’+＋&＆]")

STAGE_HINTS = [
    ("preorder", ("预售", "开订", "预出", "定金", "补款", "预约")),
    ("released", ("现货", "大货", "发售", "上市", "上线", "开售")),
    ("reprint", ("再版", "复刻")),
    ("discontinued", ("停产", "停售")),
    ("teaser", ("灰模", "试模", "剪影", "官图", "预告", "实物")),
    ("announced", ("公布", "解禁", "登场", "亮相", "新品", "公开")),
]
EVENT_HINTS = [
    ("price_change", ("跳水", "价格", "涨价", "降价", "调整")),
    ("delay", ("延期", "跳票")),
    ("review", ("测评", "开箱")),
    ("accessory", ("配件", "特典")),
]


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return PUNCT.sub("", text)


BRAND_SUFFIXES = ("工作室", "模型", "模玩", "工坊", "科技", "工业", "玩具", "公司")


def normalize_brand(name: str) -> str:
    key = norm(name)
    for suffix in BRAND_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            key = key[: -len(suffix)]
    return key


def display_stage(status: str) -> tuple[str, str]:
    for stage, words in STAGE_HINTS:
        if any(word in status for word in words):
            for event, keys in EVENT_HINTS:
                if any(key in status for key in keys):
                    return stage, event
            return stage, "none"
    for event, keys in EVENT_HINTS:
        if any(key in status for key in keys):
            return "unknown", event
    return "unknown", "none"


def load_mentions(directory: Path, start: str, end: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not (start <= payload["date"] <= end):
            continue
        for item in payload.get("items", []):
            rows.append({**item, "date": payload["date"], "video_id": payload["video_id"]})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mentions-dir", type=Path, default=Path("outputs/daily_v2/v3/mentions"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2/v3"))
    parser.add_argument("--start-date", default="00000000")
    parser.add_argument("--end-date", default="99999999")
    args = parser.parse_args()

    rows = load_mentions(args.mentions_dir, args.start_date, args.end_date)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(normalize_brand(row["brand"]), norm(row["product"]))].append(row)

    products: list[dict[str, Any]] = []
    for index, ((brand_key, product_key), mentions) in enumerate(
        sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])), 1
    ):
        mentions.sort(key=lambda row: row["date"])
        timeline = []
        for row in mentions:
            stage, event = display_stage(row.get("status", ""))
            timeline.append({
                "date": row["date"],
                "stage": stage,
                "event": event,
                "stage_cue": row.get("status", ""),
                "price": row.get("price", ""),
                "release_date": row.get("release_date", ""),
                "variant": "",
                "evidence": row.get("evidence", ""),
                "video_id": row["video_id"],
                "start": row.get("time"),
                "confidence": row.get("confidence", 0.8),
            })
        products.append({
            "id": f"Q{index:04d}",
            "brand": mentions[0]["brand"],
            "model_name": mentions[0]["product"],
            "name_key": product_key,
            "variants": [],
            "mention_count": len(mentions),
            "timeline": timeline,
            "current_stage": timeline[-1]["stage"] if timeline else "unknown",
            "flags": [],
            "mentions": mentions,
        })

    review = []
    for i, left in enumerate(products):
        for right in products[i + 1:]:
            if left["brand"] != right["brand"]:
                continue
            score = difflib.SequenceMatcher(None, left["name_key"], right["name_key"]).ratio()
            if 0.75 <= score < 1.0:
                review.append({
                    "kind": "look-alike",
                    "score": round(score, 3),
                    "left": {"id": left["id"], "brand": left["brand"], "name": left["model_name"]},
                    "right": {"id": right["id"], "brand": right["brand"], "name": right["model_name"]},
                })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    multi = [p for p in products if p["mention_count"] > 1]
    print(f"条目 {len(rows)} → 产品 {len(products)} | 多提及 {len(multi)} | 复核对 {len(review)}")
    for product in sorted(multi, key=lambda p: -p["mention_count"])[:10]:
        print(f"  {product['id']} {product['brand']} | {product['model_name']} ×{product['mention_count']} "
              f"{[t['date'] for t in product['timeline']]}")


if __name__ == "__main__":
    main()
