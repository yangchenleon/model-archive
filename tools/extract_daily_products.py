"""V3 extraction: the simplest possible product-mention extractor.

No stage enum, no field splitting, no domain vocabulary. The model reports what
the video says: brand, the product name as written, the status phrase as spoken,
price/date if present, and the supporting quote. Identity is deliberately left
to a later exact-match step.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.config import load_env
from tools.extract_daily_news import call_llm_json

load_env()

PROMPT = """你是信息提取器。从下面的视频字幕文本中，提取所有被提到的"产品条目"。

每个条目输出以下字段：
- brand：厂商/品牌名称（按原文，不要补全或改写）
- product：产品的完整名称（按原文，包含型号、版本、配色、套装等后缀，不要拆分、不要省略）
- status：这次提到的动态，用原文短语（例如"新品公布""开启预售""现货发售""价格跳水""延期""测评"）
- price：原文提到的价格（没有就留空字符串）
- release_date：原文提到的发售/出货时间（没有就留空字符串）
- evidence：支撑该条目的原文片段，不超过 40 字
- confidence：0-1，名称或信息不清晰时降低

规则：
1. 只提取具体的产品实体，不提取品牌动态、市场评论、个人感受。
2. 同一产品在同一条文本里多次出现，合并成一条。
3. 名称一律保留原文用词，不要改写、不要归纳、不要翻译。
4. 不确定就留空，不要猜测。

只返回纯 JSON：
{"items": [{"brand": "", "product": "", "status": "", "price": "", "release_date": "", "evidence": "", "confidence": 0.0}]}

视频日期：@@DATE@@
字幕文本：
@@TEXT@@
"""


def build_prompt(text: str, date: str) -> str:
    return PROMPT.replace("@@DATE@@", date).replace("@@TEXT@@", text)


def clean_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise RuntimeError(f"unexpected LLM payload: {str(payload)[:200]}")
    cleaned: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        brand = str(raw.get("brand") or "").strip()
        product = str(raw.get("product") or "").strip()
        if not brand or not product:
            continue
        try:
            confidence = float(raw.get("confidence", 0.8))
        except (TypeError, ValueError):
            confidence = 0.8
        cleaned.append({
            "brand": brand,
            "product": product,
            "status": str(raw.get("status") or "").strip(),
            "price": str(raw.get("price") or "").strip(),
            "release_date": str(raw.get("release_date") or "").strip(),
            "evidence": str(raw.get("evidence") or "").strip()[:120],
            "confidence": max(0.0, min(1.0, confidence)),
        })
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subtitles-dir", type=Path, default=Path("outputs/daily_v2/subtitles"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2/v3/mentions"))
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    subs = sorted(
        p for p in args.subtitles_dir.glob("*.json")
        if not p.name.startswith("_") and args.start_date <= p.stem[:8] <= args.end_date
    )
    if args.limit:
        subs = subs[: args.limit]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"待提取 {len(subs)} 条", flush=True)

    for index, path in enumerate(subs, 1):
        date = path.stem[:8]
        out = args.output_dir / path.name
        if out.exists() and not args.force:
            print(f"[{index}/{len(subs)}] {path.stem} 已存在，跳过", flush=True)
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = payload.get("text", "").strip()
        cues = payload.get("cues") or []
        t0 = time.time()
        try:
            items = clean_items(call_llm_json(build_prompt(text, date)))
        except Exception as exc:
            print(f"[{index}/{len(subs)}] {path.stem} FAILED: {str(exc)[:160]}", flush=True)
            continue
        for item in items:
            for cue in cues:
                if item["evidence"][:6] and item["evidence"][:6] in cue["text"]:
                    item["time"] = cue["start"]
                    break
        out.write_text(json.dumps({
            "date": date,
            "video_id": path.stem.split("_")[1],
            "items": items,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(subs)}] {path.stem} {len(items)} 条 ({time.time() - t0:.0f}s)", flush=True)
        time.sleep(args.sleep)


if __name__ == "__main__":
    main()
