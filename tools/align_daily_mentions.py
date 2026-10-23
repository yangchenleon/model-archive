"""Align daily v2 mentions into product entities and project their stage history.

The extractor emits one row per mention; this module resolves those mentions to
a single product across days and keeps the full stage timeline, so the product
directory stays one-row-per-product while every pre-release update is auditable.

Artifacts: ``products.json`` (entities + timelines), ``review.json`` (ambiguous
pairs that need a human), ``summary.json`` (counts and flags).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PUNCT = re.compile(r"[\s\-_/·・,，。.、()（）\[\]【】:：;；!！?？'\"“”‘’+＋&＆]")
GRADES = ["mgsd", "pgu", "pg", "mg", "rg", "hg", "fm", "re", "sd", "tv", "1/100", "1/144", "1/60", "1/72"]
BRAND_SUFFIXES = ["工作室", "模型", "模玩", "工坊", "工房", "科技", "工业", "玩具", "公司", "官方", "社"]
STAGE_RANK = {
    "rumor": 0, "teaser": 1, "announced": 2, "preorder": 3,
    "released": 4, "reprint": 5, "discontinued": 6, "unknown": -1,
}
# A kit and its accessory/limited add-on are different SKUs even when the base
# model name matches, so these variants must not be folded into the kit.
ACCESSORY_HINTS = ("配件包", "配件", "套装", "特典", "外甲", "改件", "头雕", "武器包", "浮游炮", "战损", "透明")

# Editorial aliases that fuzzy matching cannot reach (ASR swaps a syllable).
BRAND_SEED = {
    "supa": "SUPA",
    "sopa": "SUPA",
    "sofa": "SUPA",
    "摩showtoys": "MOSHOWTOYS",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return PUNCT.sub("", text)


def brand_key(brand: str) -> str:
    key = norm(brand)
    for suffix in BRAND_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            key = key[: -len(suffix)]
    return BRAND_SEED.get(key, key)


def grade_of(line: str, model: str) -> str:
    joined = norm(f"{line} {model}")
    for grade in GRADES:  # longest first
        if grade in joined:
            return grade
    return ""


def name_key(model: str) -> str:
    key = norm(model)
    for grade in GRADES:
        key = key.replace(grade, "")
    return key


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


REVIEW_HINTS = ("测评", "开箱")
RELEASE_EVIDENCE = ("大货", "现货", "发售", "发货", "跳水", "开售")


def reconcile_stage(item: dict[str, Any]) -> str:
    """Media samples ("测评") are not a release unless the same mention says so.

    The extractor occasionally reads "正式上线测评" as ``released``; this rule
    keeps the raw observation but reconciles the stage used for projection.
    """
    stage = item["stage"]
    if stage not in ("released", "reprint"):
        return stage
    text = f"{item.get('evidence', '')} {item.get('stage_cue', '')}"
    if any(hint in text for hint in REVIEW_HINTS) and not any(hint in text for hint in RELEASE_EVIDENCE):
        return "announced"
    return stage


def load_mentions(mentions_dir: Path, start: str | None, end: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(mentions_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        date = payload["date"]
        if start and date < start:
            continue
        if end and date > end:
            continue
        for index, item in enumerate(payload.get("mentions") or []):
            rows.append({
                **item,
                "stage_raw": item["stage"],
                "stage": reconcile_stage(item),
                "date": date,
                "video_id": payload["video_id"],
                "title": payload.get("title", ""),
                "mention_id": f"{date}_{payload['video_id']}_{index}",
            })
    rows.sort(key=lambda row: (row["date"], row["mention_id"]))
    return rows


def canonical_brands(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Cluster brand spellings (suffix-stripped) and pick the most frequent form."""
    variants: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        variants[brand_key(row["brand"])][row["brand"]] += 1

    keys = sorted(variants)
    parent = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if similarity(a, b) >= 0.85:
                union(a, b)

    clusters: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        clusters[find(key)].append(key)

    resolved: dict[str, str] = {}
    for members in clusters.values():
        counter: Counter = Counter()
        for member in members:
            counter.update(variants[member])
        canonical = counter.most_common(1)[0][0]
        for member in members:
            for raw in variants[member]:
                resolved[raw] = canonical
    return resolved


def align(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    brand_map = canonical_brands(rows)
    products: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    exact: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in rows:
        brand = brand_map.get(row["brand"], row["brand"])
        grade = grade_of(row["line"], row["model_name"])
        key_text = name_key(row["model_name"])
        accessory = bool(row["variant"]) and any(hint in norm(row["variant"]) for hint in ACCESSORY_HINTS)
        if row["event"] == "accessory" and not accessory:
            accessory = True
            if row["variant"]:
                row = {**row, "variant": row["variant"] + "配件"}

        if accessory:
            key_text = norm(row["variant"]) + key_text
        key = (brand, grade, key_text, accessory)

        product = exact.get(key)
        if product is None:
            # fuzzy fallback: same brand, compatible grade, very similar name
            best = None
            for candidate in products:
                if candidate["brand"] != brand or candidate.get("accessory") != accessory:
                    continue
                if candidate["grade"] and grade and candidate["grade"] != grade:
                    continue
                score = similarity(candidate["name_key"], key_text)
                if score >= 0.90 and (best is None or score > best[1]):
                    best = (candidate, score)
            if best:
                product, score = best
                product.setdefault("match_methods", Counter())["fuzzy"] += 1
                product.setdefault("match_scores", []).append(round(score, 3))
            else:
                for candidate in products:
                    if candidate["brand"] != brand or candidate.get("accessory") != accessory:
                        continue
                    if candidate["grade"] and grade and candidate["grade"] != grade:
                        continue
                    score = similarity(candidate["name_key"], key_text)
                    if 0.80 <= score < 0.90:
                        review.append({
                            "kind": "fuzzy-name",
                            "score": round(score, 3),
                            "left": {"product": candidate["id"], "brand": candidate["brand"], "name": candidate["model_name"]},
                            "right": {"brand": brand, "name": row["model_name"], "date": row["date"]},
                        })
                product = {
                    "id": f"P{len(products) + 1:04d}",
                    "brand": brand,
                    "grade": grade,
                    "line": row["line"],
                    "model_name": row["model_name"],
                    "name_key": key_text,
                    "accessory": accessory,
                    "variants": set(),
                    "brand_aliases": set(),
                    "sources": set(),
                    "mentions": [],
                    "match_methods": Counter(),
                    "match_scores": [],
                }
                products.append(product)
                exact[key] = product

        product["mentions"].append(row)
        product["variants"].add(row["variant"])
        product["brand_aliases"].add(row["brand"])
        product["sources"].add(row["video_id"])
        product.setdefault("match_methods", Counter())["exact"] += 1

    for product in products:
        product["variants"] = sorted(v for v in product["variants"] if v)
        product["brand_aliases"] = sorted(product["brand_aliases"])
        product["sources"] = sorted(product["sources"])
        product["match_methods"] = dict(product["match_methods"])
        product["mention_count"] = len(product["mentions"])
        product["first_seen"] = product["mentions"][0]["date"]
        product["last_seen"] = product["mentions"][-1]["date"]
        timeline = []
        for mention in product["mentions"]:
            timeline.append({
                "date": mention["date"],
                "stage": mention["stage"],
                "stage_raw": mention.get("stage_raw", mention["stage"]),
                "event": mention["event"],
                "stage_cue": mention.get("stage_cue", ""),
                "price": mention["price"],
                "release_date": mention["release_date"],
                "variant": mention["variant"],
                "evidence": mention["evidence"],
                "video_id": mention["video_id"],
                "start": (mention.get("source_time") or {}).get("start"),
                "confidence": mention["confidence"],
            })
        product["timeline"] = timeline
        product["current_stage"] = _projected_stage(timeline)
        product["flags"] = [flag for flag in _flags(timeline) if flag]
        dates = defaultdict(set)
        for entry in timeline:
            if entry["variant"]:
                dates[entry["date"]].add(entry["variant"])
        for date, variants in sorted(dates.items()):
            if len(variants) > 1:
                product["flags"].append({"type": "same_day_variants", "date": date, "variants": sorted(variants)})
        for mention in product["mentions"]:
            mention.pop("title", None)
    return products, review, brand_map


def _projected_stage(timeline: list[dict[str, Any]]) -> str:
    """Furthest stage reached by a stage announcement.

    Price/review/accessory updates describe events around the current stage, so
    they are ignored unless the product never had a plain stage announcement.
    """
    def furthest(entries: list[dict[str, Any]]) -> str:
        best_rank, best_stage = -1, "unknown"
        for entry in entries:
            rank = STAGE_RANK.get(entry["stage"], -1)
            if rank > best_rank:
                best_rank, best_stage = rank, entry["stage"]
        return best_stage

    stage_entries = [entry for entry in timeline if entry["event"] == "none"]
    return furthest(stage_entries or timeline)


def _flags(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Explainable anomalies: a plain stage claim going backwards, or a price
    change recorded before the product was ever released."""
    flags: list[dict[str, Any]] = []
    for prev, cur in zip(timeline, timeline[1:]):
        a, b = STAGE_RANK.get(prev["stage"], -1), STAGE_RANK.get(cur["stage"], -1)
        # price/review/accessory/info updates are events, not a rollback.
        if cur["event"] == "none" and a >= 0 and b >= 0 and b < a and cur["stage"] not in ("reprint", "discontinued"):
            flags.append({"type": "stage_regression", "from": prev["stage"], "to": cur["stage"], "date": cur["date"]})
        if cur["event"] == "price_change" and b < STAGE_RANK["released"]:
            flags.append({"type": "price_before_release", "stage": cur["stage"], "date": cur["date"]})
    return flags


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mentions-dir", type=Path, default=Path("outputs/daily_v2/mentions"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2"))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--report-limit", type=int, default=12)
    args = parser.parse_args()

    rows = load_mentions(args.mentions_dir, args.start_date, args.end_date)
    products, review, brand_map = align(rows)
    multi = [p for p in products if p["mention_count"] > 1]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    stage_counts = Counter()
    for product in products:
        for entry in product["timeline"]:
            stage_counts[entry["stage"]] += 1
    summary = {
        "mentions": len(rows),
        "products": len(products),
        "multi_mention_products": len(multi),
        "mentions_in_multi": sum(p["mention_count"] for p in multi),
        "review_pairs": len(review),
        "stage_counts": dict(stage_counts),
        "brands": len({p["brand"] for p in products}),
        "brand_aliases": {raw: canon for raw, canon in sorted(brand_map.items()) if raw != canon},
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"提及 {summary['mentions']} 条 -> 产品 {summary['products']} 个 "
          f"(多提及产品 {summary['multi_mention_products']} 个, 覆盖 {summary['mentions_in_multi']} 条提及)")
    print(f"待人工复核 {summary['review_pairs']} 对 | 品牌 {summary['brands']} 个")
    print("stage 分布:", dict(stage_counts))
    if summary["brand_aliases"]:
        print("品牌别名合并:", summary["brand_aliases"])

    print(f"\n=== 多提及产品 top {args.report_limit} ===")
    for product in sorted(multi, key=lambda p: -p["mention_count"])[: args.report_limit]:
        print(f"\n[{product['id']}] {product['brand']} | {product['grade']} | {product['model_name']} "
              f"(x{product['mention_count']}, {product['first_seen']}~{product['last_seen']}, 当前 {product['current_stage']})")
        for entry in product["timeline"]:
            print(f"   {entry['date']}  {entry['stage']:10s} {entry['event']:12s} "
                  f"{entry['price'] or '-':8s} {entry['variant'] or ''} | {(entry['stage_cue'] or entry['evidence'])[:28]}")
        for flag in product["flags"]:
            print(f"   ⚠ {flag}")


if __name__ == "__main__":
    main()
