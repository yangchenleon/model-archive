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

PROMPT = """你是模玩（拼装模型、成品机甲、可动人偶、特摄周边）资讯的信息提取器。
输入是 B 站模玩速报视频的字幕文本，口播里常有同音错别字，请结合上下文纠正名称，但不要改变产品身份。

背景常识：
- GK 是一种套件类型，不是厂牌，不要放进 brand。
- "新厂""某厂""某工作室"未具名时，brand 留空，不要臆造。
- "B社/代哥/万代" 指同一家厂商；"国服/日系" 不是厂商。

每个条目输出：
- brand：厂商名，只填厂商；空则留空字符串
- line：产品线/规格（MG、RG、PGU、MGSD、1比60拼装、超动骑兵系列…），没有就留空
- product：产品基础名称（机体/角色/型号），只保留名词，不含版本词和动词
- variant：版本/配色/换色/限定/套装等修饰（电镀银、海涅配色、进阶装、PB限定、战损配件包…），没有就留空
- status：产品当前生命周期状态，只能取以下值之一
  rumor（传闻/爆料）、teaser（灰模/试模/剪影/官图）、announced（公布/解禁/登场）、
  preorder（预售/开订/定金/先行）、released（现货/大货/发售/上线）、
  reprint（再版/复刻）、discontinued（停产/停售）、unknown
- price：价格，只保留数字和单位，没有就留空
- detail：其他描述性信息（测评、延期、配件、玩法、价格波动、评价等），不要塞进上面任何字段
- evidence：支撑该条目的原文片段，不超过 40 字
- confidence：0-1

规则：
1. 只提取具体产品，不提取品牌动态、市场评论、纯个人感受。
2. 同一产品在同一条文本里多次出现，合并成一条。
3. product 必须是纯名词短语，不含动词、感叹、状态词；版本/配色一律进 variant。
4. brand 与 product 边界要清楚：厂商名只出现在 brand，系列名只出现在 line。
5. status 只能从枚举里选；拿不准选 unknown。
6. 不确定就留空，不要猜测。
7. 福利/抽奖/掉落/赠品内容不是产品资讯：出现"掉落""抽奖""福利""赠送""开奖""上车""粉丝福利"等词的段落，
   整段不要提取；"包含了 A、B、C"这种罗列通常是赠品清单，也不要拆成产品条目。
8. 广告/带货/店铺引流（"XX 家上新""链接在橱窗"等）同样不提取。

只返回纯 JSON：
{"items": [{"brand": "", "line": "", "product": "", "variant": "", "status": "unknown", "price": "", "detail": "", "evidence": "", "confidence": 0.0}]}

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
            "line": str(raw.get("line") or "").strip(),
            "product": product,
            "variant": str(raw.get("variant") or "").strip(),
            "status": str(raw.get("status") or "unknown").strip().lower(),
            "price": str(raw.get("price") or "").strip(),
            "detail": str(raw.get("detail") or "").strip()[:200],
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
