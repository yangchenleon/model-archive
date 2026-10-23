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


BRAND_SUFFIXES = ("工作室", "模型", "模玩", "工坊", "科技", "工业", "玩具", "公司", "配件包")


def normalize_brand(name: str) -> str:
    key = norm(name)
    for suffix in BRAND_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            key = key[: -len(suffix)]
    return key


GRADE_PREFIX = re.compile(r"^(PGU|MGSD|MGEX|MG|RG|HG|PG|FM|RE|SD|TV)(?=[一-鿿])")


def normalize_product(product: str, line: str) -> tuple[str, str]:
    """Move a scale token that leaked into product back to line (deterministic)."""
    match = GRADE_PREFIX.match(product or "")
    if not match:
        return product, line
    return product[match.end():], line or match.group(1)


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
            product, line = normalize_product(item.get("product", ""), item.get("line", ""))
            rows.append({**item, "product": product, "line": line,
                         "date": payload["date"], "video_id": payload["video_id"]})
    return rows


def load_aliases(path: Path) -> dict[tuple[str, str], str]:
    """Confirmed aliases: (brand key, observed product key) -> canonical product key."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        (normalize_brand(entry["brand"]), norm(entry["from"])): norm(entry["to"])
        for entry in payload.get("aliases", [])
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mentions-dir", type=Path, default=Path("outputs/daily_v2/v3/mentions"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2/v3"))
    parser.add_argument("--alias-file", type=Path, default=Path("outputs/daily_v2/alias.json"))
    parser.add_argument("--start-date", default="00000000")
    parser.add_argument("--end-date", default="99999999")
    args = parser.parse_args()

    rows = load_mentions(args.mentions_dir, args.start_date, args.end_date)
    aliases = load_aliases(args.alias_file)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        brand_key = normalize_brand(row["brand"])
        product_key = aliases.get((brand_key, norm(row["product"])), norm(row["product"]))
        groups[(brand_key, product_key, norm(row.get("variant", "")))].append(row)

    products: list[dict[str, Any]] = []
    for index, ((brand_key, product_key, variant_key), mentions) in enumerate(
        sorted(groups.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])), 1
    ):
        mentions.sort(key=lambda row: row["date"])
        timeline = []
        for row in mentions:
            status = row.get("status", "") or "unknown"
            stage, event = display_stage(status)
            if stage == "unknown" and status in ("rumor", "teaser", "announced", "preorder",
                                                 "released", "reprint", "discontinued"):
                stage = status
            detail = row.get("detail", "")
            if any(word in detail for word in ("跳水", "涨价", "降价", "价格调整")):
                event = "price_change"
            elif "延期" in detail:
                event = "delay"
            elif "测评" in detail or "开箱" in detail:
                event = "review"
            timeline.append({
                "date": row["date"],
                "stage": stage,
                "event": event,
                "stage_cue": row.get("status", ""),
                "price": row.get("price", ""),
                "release_date": "",
                "variant": row.get("variant", ""),
                "detail": detail,
                "evidence": row.get("evidence", ""),
                "video_id": row["video_id"],
                "start": row.get("time"),
            })
        products.append({
            "id": f"Q{index:04d}",
            "brand": mentions[0]["brand"],
            "model_name": mentions[0]["product"],
            "line": mentions[0].get("line", ""),
            "name_key": product_key,
            "variants": sorted({row.get("variant", "") for row in mentions if row.get("variant")}),
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
