"""V2 extraction: turn one transcript into atomic product mentions.

Unlike the legacy ``extract_daily_news`` (one free-form ``news_type`` string per
item), every mention here carries a controlled ``stage``, an orthogonal
``event``, and a split product identity (``brand`` / ``line`` / ``model_name`` /
``variant``) so that mentions can be aligned into one product across days.

Stage axis (observed sales life-cycle, implied by what the video says):

    rumor -> teaser -> announced -> preorder -> released -> discontinued
                                             \\-> reprint -> released

Event axis (does not advance the stage): info_update, price_change, delay,
review, accessory, payment, expo, recall.

Artifacts: ``<out>/<YYYYMMDD>_<BV>.json`` with the parsed mentions.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.config import load_env
from tools.extract_daily_news import call_llm_json

load_env()

STAGES = [
    "rumor",        # 传闻/爆料/剪影，官方未确认
    "teaser",       # 预告/灰模/试模/展会实物，已有实物但未公布发售
    "announced",    # 官方公布/解禁/登场/亮相，尚未开订
    "preorder",     # 预售/开订/定金/先行
    "released",     # 现货/大货/正式发售/上线
    "reprint",      # 再版/换色再版/复刻
    "discontinued", # 停产/停售/绝版
    "unknown",      # 无法判断
]
EVENTS = [
    "none",         # 纯阶段推进
    "info_update",  # 官图更新/实物图/试模进度
    "price_change", # 价格跳水/调整/涨价
    "delay",        # 延期/跳票
    "review",       # 测评/开箱
    "accessory",    # 配件包/特典公布
    "payment",      # 补款/尾款
    "expo",         # 展会限定/场限
    "recall",       # 召回/修复/下架
]

PROMPT = """你是模玩资讯的数据提取器。请把这段模玩速报视频的语音转写，拆成一条条"产品提及"（mention）。

【产品身份拆分】每个产品必须拆成四段，不要混在一起：
- brand：厂商/品牌（如 瘦虎模型、大班、摩动核、万代、酋长大陆）
- line：产品线/规格前缀（如 MG、RG、PGU、MGSD、HG、超动骑兵系列、机神维度系列；没有则留空）
- model_name：核心机体/角色/型号名（如 巴巴托斯天狼座、牛高达、诺姆、流星），不要带价格、日期、发售状态
- variant：版本/配色/限定/套装（如 PB限定、彩透外甲、海涅配色、战损配件包；没有则留空）

【stage：产品当前的销售阶段，只能取以下值之一】
- rumor：传闻/爆料/剪影，官方未确认
- teaser：预告/灰模/试模/展会实物展示，已有实物或官图但未公布发售
- announced：官方公布/解禁/登场/亮相，尚未开订
- preorder：出现"预出/预售/开订/定金/先行/预订/餐券/预约/众筹"等字样（即使同时说"登场/上线"，也按预售）
- released：明确说"现货/大货/已发售/正式发售/上市/到货/发货"（价格跳水也属于已发售）
- reprint：再版/换色再版/复刻
- discontinued：停产/停售/绝版
- unknown：无法判断

【event：这条资讯的事件类型，与 stage 正交，只能取以下值之一】
- none：纯粹的阶段推进（如新品公布、预售开订、现货发售）
- info_update：官图更新、实物图、试模进度、灰模
- price_change：价格跳水、涨价、价格调整
- delay：延期、跳票
- review：测评、开箱
- accessory：配件包、特典公布
- payment：补款、尾款
- expo：展会限定、场限发售
- recall：召回、修复、下架

【提取规则】
1. 语音转写有同音错别字，请结合标题、简介与模玩领域知识自动纠偏（如 DMS/TMS、超动/超重骑兵、追击/追迹、御兔/玉兔、SOPA/SUPA）。
2. 价格按口播常识还原（"六八"=68元，"十九点八"=19.8元），不要放大十倍，不要把型号当价格（如"大班6613"）。
3. 跳过：粉丝抽奖/个人福利、纯主观评价无产品信息、与模玩无关的闲聊。
4. 同一产品在同一条视频里多次出现，只输出一条，合并信息。
5. price 未提及留空字符串；release_date 未提及留空字符串。
6. evidence 摘录转写中支撑该条目的原文片段，不超过 40 字。
7. confidence：0-1，转写清晰且产品明确取 0.9 以上，名称存疑或信息零散取 0.5-0.7。
8. stage_cue：摘录你据以判定 stage 的原话关键词（如"预出七十八""现货发售""正式公布"），不超过 20 字；判断不了留空。
9. 不确定时宁可选 unknown/announced，不要猜成 released。
10. 测评/开箱类内容：event=review；除非原话明确说了"大货/现货/已发售/发货"，否则 stage 取 announced（媒体样件/测评件不等于已发售）。

【输出】只返回纯 JSON，不要 Markdown：
{
  "items": [
    {
      "brand": "",
      "line": "",
      "model_name": "",
      "variant": "",
      "scale": "",
      "stage": "announced",
      "stage_cue": "",
      "event": "none",
      "price": "",
      "release_date": "",
      "evidence": "",
      "confidence": 0.9
    }
  ]
}

视频标题：@@TITLE@@
发布日期：@@DATE@@
视频简介：@@DESC@@
语音转写：
@@TRANSCRIPT@@

请只返回纯 JSON 对象。"""


def build_prompt(transcript: str, metadata: dict[str, Any], date: str) -> str:
    return (
        PROMPT.replace("@@TITLE@@", metadata.get("title") or "")
        .replace("@@DATE@@", date)
        .replace("@@DESC@@", (metadata.get("description") or "")[:500])
        .replace("@@TRANSCRIPT@@", transcript)
    )


def clean_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Coerce one raw item to the controlled schema; drop it when unusable."""
    brand = str(item.get("brand") or "").strip()
    model = str(item.get("model_name") or "").strip()
    if not brand or not model:
        return None
    stage = str(item.get("stage") or "unknown").strip().lower()
    event = str(item.get("event") or "none").strip().lower()
    if stage not in STAGES:
        stage = "unknown"
    if event not in EVENTS:
        event = "none"
    try:
        confidence = float(item.get("confidence", 0.8))
    except (TypeError, ValueError):
        confidence = 0.8
    return {
        "brand": brand,
        "line": str(item.get("line") or "").strip(),
        "model_name": model,
        "variant": str(item.get("variant") or "").strip(),
        "scale": str(item.get("scale") or "").strip(),
        "stage": stage,
        "stage_cue": str(item.get("stage_cue") or "").strip()[:40],
        "event": event,
        "price": str(item.get("price") or "").strip(),
        "release_date": str(item.get("release_date") or "").strip(),
        "evidence": str(item.get("evidence") or "").strip()[:120],
        "confidence": max(0.0, min(1.0, confidence)),
    }


def extract_one(transcript: str, metadata: dict[str, Any], date: str, model: str | None = None) -> list[dict[str, Any]]:
    payload = call_llm_json(build_prompt(transcript, metadata, date), model_override=model)
    raw_items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(raw_items, list):
        raise RuntimeError(f"unexpected LLM payload: {str(payload)[:200]}")
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        cleaned = clean_item(raw) if isinstance(raw, dict) else None
        if cleaned:
            items.append(cleaned)
    return items


def locate_cue(evidence: str, cues: list[dict[str, Any]]) -> tuple[float, float] | None:
    """Find the subtitle cue that best matches a mention's evidence."""
    if not evidence or not cues:
        return None
    for cue in cues:
        if evidence[:8] and evidence[:8] in cue["text"]:
            return cue["start"], cue["end"]
    best = max(cues, key=lambda cue: difflib.SequenceMatcher(None, evidence, cue["text"]).ratio())
    ratio = difflib.SequenceMatcher(None, evidence, best["text"]).ratio()
    return (best["start"], best["end"]) if ratio >= 0.5 else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reports-dir", type=Path, default=Path("outputs/daily_reports"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_v2/mentions"))
    parser.add_argument("--start-date", required=True, help="YYYYMMDD")
    parser.add_argument("--end-date", required=True, help="YYYYMMDD")
    parser.add_argument("--model", help="LLM model override")
    parser.add_argument("--source", choices=["asr", "ocr"], default="asr")
    parser.add_argument("--subtitles-dir", type=Path, default=Path("outputs/daily_v2/subtitles"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    pattern = re.compile(r"^(\d{8})_(BV\w+)$")
    days = []
    for path in sorted(args.reports_dir.iterdir()):
        match = pattern.match(path.name)
        if not match or not (path / "video").is_dir():
            continue
        day = match.group(1)
        if not (args.start_date <= day <= args.end_date):
            continue
        days.append((day, match.group(2), path))
    if args.limit:
        days = days[: args.limit]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"待提取 {len(days)} 天", flush=True)
    failures = 0
    for index, (day, bvid, path) in enumerate(days, 1):
        out_path = args.output_dir / f"{day}_{bvid}.json"
        if out_path.exists() and not args.force:
            print(f"[{index}/{len(days)}] {day} {bvid} 已存在，跳过", flush=True)
            continue
        info_files = sorted((path / "video").glob("*.info.json"))
        if not info_files:
            print(f"[{index}/{len(days)}] {day} {bvid} 缺元数据，跳过", flush=True)
            failures += 1
            continue
        metadata = json.loads(info_files[0].read_text(encoding="utf-8"))
        cues: list[dict[str, Any]] = []
        if args.source == "ocr":
            sub_path = args.subtitles_dir / f"{day}_{bvid}.json"
            if not sub_path.exists():
                print(f"[{index}/{len(days)}] {day} {bvid} 缺 OCR 字幕，跳过", flush=True)
                failures += 1
                continue
            sub_payload = json.loads(sub_path.read_text(encoding="utf-8"))
            transcript = sub_payload.get("text", "").strip()
            cues = sub_payload.get("cues") or []
        else:
            transcript_files = sorted((path / "transcript").glob("*.txt"))
            if not transcript_files:
                print(f"[{index}/{len(days)}] {day} {bvid} 缺转写，跳过", flush=True)
                failures += 1
                continue
            transcript = transcript_files[0].read_text(encoding="utf-8").strip()
        t0 = time.time()
        try:
            items = extract_one(transcript, metadata, day, args.model)
        except Exception as exc:
            failures += 1
            print(f"[{index}/{len(days)}] {day} {bvid} FAILED: {str(exc)[:200]}", flush=True)
            time.sleep(args.sleep)
            continue
        if cues:
            for item in items:
                span = locate_cue(item.get("evidence", ""), cues)
                if span:
                    item["source_time"] = {"start": span[0], "end": span[1]}
                    item["source_url"] = f"https://www.bilibili.com/video/{bvid}?t={int(span[0])}"
        payload = {
            "date": day,
            "source": args.source,
            "video_id": bvid,
            "source_video": metadata.get("webpage_url") or f"https://www.bilibili.com/video/{bvid}",
            "title": metadata.get("title") or "",
            "mentions": items,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        stages = {}
        for item in items:
            stages[item["stage"]] = stages.get(item["stage"], 0) + 1
        print(
            f"[{index}/{len(days)}] {day} {bvid} {len(items)} 条 {stages} ({time.time() - t0:.0f}s)",
            flush=True,
        )
        time.sleep(args.sleep)

    print(f"完成，失败 {failures} 天", flush=True)


if __name__ == "__main__":
    main()
