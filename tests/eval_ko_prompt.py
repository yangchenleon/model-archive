"""Targeted regression check for KO / third-party brand attribution.

The extractor's world knowledge maps famous Bandai kits (Nu Gundam, Unicorn,
Phoenix...) to 万代 even when the sentence is about a third-party KO release from
大班 / 高高 / 猛虎 / 长龙 ... . These cases pin the expected brand for the
segments that were previously wrong, plus two controls where 万代 is correct
(the reviewer's sarcastic "隔壁不知名小厂万代" phrasing).

Usage:
    .venv-tools/bin/python -m tests.eval_ko_prompt
    .venv-tools/bin/python -m tests.eval_ko_prompt --only 1011
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from tools.extract_daily_news import call_llm_json
from tools.extract_daily_products import build_prompt, clean_items

REPORTS = Path("outputs/daily_reports")

# (folder, [(product substring, expected brand)], [product substrings that must not appear])
CASES: list[dict[str, Any]] = [
    {
        "name": "0704 猛虎/天硕/爆闪 把 KO 当万代",
        "folder": "20260704_BV1MnTZ68E7J",
        "expect": [("菲尼克斯", "猛虎"), ("新安洲", "天硕模型"), ("Z高达", "爆闪")],
        "forbid": [],
    },
    {
        "name": "0810 无名 KO 不应写万代",
        "folder": "20260810_BV1s7uR6QE6o",
        "expect": [("希卡利奥特曼", ""), ("报丧女妖", "SUPA")],
        "forbid": [],
        "allow_missing": True,
    },
    {
        "name": "0821 大班 PGU 元祖 / hirm 飞翼",
        "folder": "20260821_BV1iJ8M64EPM",
        "expect": [("元祖", "大班"), ("飞翼", "大班")],
        "forbid": [],
    },
    {
        "name": "0829 长龙 福风牛 / 黑金菲尼克斯",
        "folder": "20260829_BV1JhtK6WEFP",
        "expect": [("福风牛", "长龙"), ("菲尼克斯", "长龙")],
        "forbid": [],
    },
    {
        "name": "0912 大班 托鲁基斯二号机 / 全装备独角兽",
        "folder": "20260912_BV1YWYS61ERt",
        "expect": [("托鲁基斯", "大班"), ("全装备独角兽", "大班")],
        "forbid": [],
    },
    {
        "name": "0917 掉落清单不应出条目",
        "folder": "20260917_BV1tAeN6LETP",
        "expect": [],
        "forbid": ["真骨雕王蛇", "斑豹", "初号机", "斗士一型"],
    },
    {
        "name": "0928 大班 蓝异端 / 红鹦鹉",
        "folder": "20260928_BV1whaG6pEEp",
        "expect": [("蓝异端", "大班"), ("红鹦鹉", "大班")],
        "forbid": [],
    },
    {
        "name": "1003 真飞鸟剑装脉冲",
        "folder": "20261003_BV1JTHa65Eyz",
        "expect": [("剑装脉冲", "真飞鸟模型")],
        "forbid": [],
    },
    {
        "name": "1011 无名 KO 牛高达 / 万代刹帝利",
        "folder": "20261011_BV1thpL62EFA",
        "expect": [("牛高达", ""), ("刹帝利", "万代")],
        "forbid": [],
        "allow_missing": True,
    },
    {
        "name": "1016 反讽小厂仍是万代",
        "folder": "20261016_BV1bNJD66Emo",
        "expect": [("命运高达", "万代"), ("神高达", "万代"), ("黑暗迪迦", "万代")],
        "forbid": [],
    },
    {
        "name": "1022 班爷的 PGU 牛高达",
        "folder": "20261022_BV1jKny6zEde",
        "expect": [("牛高达", "大班")],
        "forbid": [],
    },
]

SUFFIX = re.compile(r"(模型|模玩|工作室)$")


def norm_brand(value: str) -> str:
    return SUFFIX.sub("", (value or "").strip())


def is_blank(value: str) -> bool:
    return (value or "").strip() in ("", "未知", "unknown", "None")


def hits(item: dict[str, Any], key: str) -> bool:
    """Match on the product name or the verbatim evidence quote.

    ASR mangles product names often enough (福风 → 福吉) that matching only the
    product would report a brand failure as a missing item.
    """
    return key in item.get("product", "") or key in item.get("evidence", "")


def evaluate(case: dict[str, Any], items: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for key, expected in case["expect"]:
        found = [item for item in items if hits(item, key)]
        if not found:
            if case.get("allow_missing"):
                continue
            failures.append(f"缺少条目 {key}")
            continue
        item = found[0]
        ok = is_blank(item["brand"]) if expected == "" else norm_brand(item["brand"]) == norm_brand(expected)
        if not ok:
            failures.append(f"{key}: 期望「{expected or '空'}」，实际「{item['brand']}」")
    for key in case["forbid"]:
        if any(hits(item, key) for item in items):
            failures.append(f"不应出现 {key}（掉落清单）")
    return failures


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    folder = REPORTS / case["folder"]
    text = json.loads((folder / "subtitles" / f"{folder.name}.json").read_text(encoding="utf-8"))["text"]
    items = clean_items(call_llm_json(build_prompt(text, folder.name[:8]), temperature=0.0), text)
    return {"name": case["name"], "folder": case["folder"], "failures": evaluate(case, items), "items": items}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", help="substring filter on folder / case name (repeatable)")
    parser.add_argument("--save", type=Path, help="write raw results as JSON")
    parser.add_argument("--replay", type=Path, help="re-score a saved --save file instead of calling the model")
    args = parser.parse_args()

    cases = [c for c in CASES if not args.only
             or any(key in c["folder"] or key in c["name"] for key in args.only)]
    saved: dict[str, Any] = {}
    if args.replay:
        saved = {entry["folder"]: entry for entry in json.loads(args.replay.read_text(encoding="utf-8"))}
    results = []
    failed = 0
    for index, case in enumerate(cases, 1):
        if args.replay:
            entry = saved[case["folder"]]
            result = {"name": case["name"], "folder": case["folder"],
                      "failures": evaluate(case, entry["items"]), "items": entry["items"]}
        else:
            result = run_case(case)
        results.append(result)
        status = "PASS" if not result["failures"] else "FAIL"
        failed += bool(result["failures"])
        print(f"[{index}/{len(cases)}] {status} {result['name']}", flush=True)
        for failure in result["failures"]:
            print(f"        - {failure}", flush=True)
        if result["failures"]:
            for item in result["items"]:
                print(f"        · {item['brand'] or '(空)'} | {item['product']} | {item['evidence'][:50]}", flush=True)

    print(f"\n{len(cases) - failed}/{len(cases)} 通过")
    if args.save:
        args.save.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"raw -> {args.save}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
