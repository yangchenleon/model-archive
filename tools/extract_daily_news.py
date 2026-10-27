"""Extract and normalize daily toy/model news from video metadata and ASR transcripts.

The module produces exactly one artifact, ``daily_report.json``; Markdown
summaries and product CSV exports are deliberately not generated here.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from tools.config import load_env

load_env()


def get_beijing_date_str(metadata: dict[str, Any], fmt: str = "%Y-%m-%d") -> str:
    """Format release timestamp in China Standard Time (UTC+8) to avoid UTC day shift."""
    ts = metadata.get("timestamp") or metadata.get("pubdate")
    if ts:
        tz_bj = datetime.timezone(datetime.timedelta(hours=8))
        return datetime.datetime.fromtimestamp(ts, tz_bj).strftime(fmt)
    raw = str(metadata.get("upload_date") or "")
    if fmt == "%Y-%m-%d" and len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


def clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks if present."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fenced:
        return fenced.group(1).strip()
    return text


def build_news_prompt(transcript: str, metadata: dict[str, Any]) -> str:
    title = metadata.get("title") or ""
    uploader = metadata.get("uploader") or "模玩速报UP主"
    upload_date = get_beijing_date_str(metadata, fmt="%Y-%m-%d")
    description = metadata.get("description") or ""

    return f"""你是一名资深模玩（机甲、拼装模型、成品合金、特摄周边、可动人偶）资讯主编。
请根据UP主“{uploader}”的模玩速报视频元数据和语音转写内容，将其整理规范化为结构化的【模玩每日速报】数据。

【核心要求与专业规范】：
1. 语音转写中必然存在模玩圈术语与品牌名称的同音错别字。请不要依赖固定映射表，而是充分自主结合视频标题、简介元数据以及模玩圈专业领域知识（涵盖拼装模型、成品合金机甲、特摄周边、GK套件等），对语音转写中出现的品牌名、机体名、缩写等进行自主纠偏与规范化（如纠正将MG识为NG、魂限定识别为TB、将知名厂商及机体名识别为同音字等情况）。
2. 价格与编号识别校准：
   - 拼装模型与配件售价通常为两位数或特定合理区间（如口播“六八”为 68元而非680元，“四五”为 45元，“十九点八”为 19.8元），请结合常理推断，不要无端放大十倍。
   - 注意区分厂商产品型号与售价（例如“大班六六一三”是指大班编号6613，并非价格）。
3. 抽奖与博主粉丝福利（如个人掉落福利、二手抽奖等个人互动）无需作为厂商产品动态。
4. 提取每一款独立模玩动态，包含字段：
   - brand: 规范的品牌/厂商名称（如 瘦虎模型、布鲁可、US模玩、高高模型、大班、摩动核、熵玩、伊甸工业、暗源JoyToy 等）
   - product_name: 规范完整的产品名称（如 MG 巴巴托斯天狼座）
   - category_scale: 规格/比例/类型（如 MG 1/100 拼装、MGSD 拼装、成品合金机甲、可动人偶、拼装配件包 等）
   - news_type: 动态类型（如 新品公布 / 预售开订 / 现货发售 / 价格跳水 / 官图更新 / 配件公布）
   - price: 准确价格信息（若有，如 68元、149元单体，未提及则留空字符串）
   - release_date: 预计发售或出货时间（若有，如 2026年9月底、10月中旬，未提及则留空字符串）
   - details: 核心速报内容、产品亮点、附带配件、玩法、竞品动态及UP评价。

【输出要求】：
重点提取准确的产品条目信息，无需撰写宏观总结或市场分析。
请以纯合法 JSON 格式输出，顶层结构如下：
{{
  "report_title": "精炼速报总标题",
  "report_date": "资讯所属日期，格式YYYY-MM-DD",
  "news_items": [
    {{
      "brand": "...",
      "product_name": "...",
      "category_scale": "...",
      "news_type": "...",
      "price": "...",
      "release_date": "...",
      "details": "..."
    }}
  ]
}}

视频标题：{title}
发布日期：{upload_date}
视频简介：{description}
语音转写内容：
{transcript}

请只返回纯 JSON 对象，不要附加任何 Markdown 格式或前后说明。"""


def _post_chat_completions(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 120, temperature: float = 0.1) -> str:
    payload = json.dumps({
        "model": model,
        "temperature": temperature,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    return res["choices"][0]["message"]["content"]


def call_llm_json(prompt: str, model_override: str | None = None, temperature: float = 0.1) -> dict[str, Any]:
    """Call LLM with fallback between configured LLM endpoint and DashScope endpoint."""
    llm_key = os.getenv("LLM_API_KEY")
    llm_base = os.getenv("LLM_BASE_URL")
    llm_model = model_override or os.getenv("LLM_MODEL", "Qwen3.5-35B-A3B")

    asr_key = os.getenv("ASR_API_KEY")
    asr_base = os.getenv("ASR_BASE_URL")

    # List of candidate endpoints to try in order
    candidates: list[tuple[str, str, str]] = []
    if llm_base and llm_key:
        candidates.append((llm_base, llm_key, llm_model))

    # DashScope compatible MaaS endpoint fallback
    if asr_base and asr_key and (asr_base != llm_base or asr_key != llm_key):
        candidates.append((asr_base, asr_key, "qwen-plus"))

    if not candidates:
        raise RuntimeError("No LLM or ASR API credentials configured in environment.")

    last_error: Exception | None = None
    for base_url, key, model in candidates:
        try:
            raw_text = _post_chat_completions(base_url, key, model, prompt, timeout=150, temperature=temperature)
            cleaned = clean_json_text(raw_text)
            return json.loads(cleaned)
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"All LLM endpoints failed. Last error: {last_error}")


def extract_daily_news(
    transcript: str,
    metadata: dict[str, Any],
    output_dir: Path,
    model_override: str | None = None,
) -> dict[str, Any]:
    """Execute daily news extraction and persist ``daily_report.json`` only."""
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = build_news_prompt(transcript, metadata)
    report_data = call_llm_json(prompt, model_override=model_override)

    # Attach provenance & raw ASR transcript to structured JSON
    source_url = metadata.get("webpage_url") or metadata.get("url") or ""
    report_data["source_url"] = source_url
    report_data["source_title"] = metadata.get("title") or ""
    report_data["uploader"] = metadata.get("uploader") or ""
    bj_date = get_beijing_date_str(metadata, fmt="%Y-%m-%d")
    report_data["upload_date"] = bj_date
    if not report_data.get("report_date"):
        report_data["report_date"] = bj_date
    report_data["raw_transcript"] = transcript

    json_path = output_dir / "daily_report.json"
    json_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"report_data": report_data, "json_path": str(json_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript_file", type=Path, help="Path to transcript JSON or TXT")
    parser.add_argument("--metadata", type=Path, required=True, help="Path to video metadata JSON")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for reports")
    parser.add_argument("--model", help="Optional LLM model override")
    args = parser.parse_args()

    trans_raw = args.transcript_file.read_text(encoding="utf-8")
    try:
        trans_obj = json.loads(trans_raw)
        transcript = trans_obj.get("text", "")
    except Exception:
        transcript = trans_raw

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    res = extract_daily_news(transcript, metadata, args.output_dir, model_override=args.model)
    print(json.dumps({
        "json": res["json_path"],
        "item_count": len(res["report_data"].get("news_items", [])),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
