"""Extract product rows from a transcript into the archive CSV template."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

CSV_FIELDS = ["厂商", "产品编号", "来源类型", "产品线", "模型名称", "版本/配色", "详情", "资料来源"]


def _json_from_text(text: str) -> Any:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start < 0 or end < start:
        raise ValueError("LLM response does not contain a JSON array")
    return json.loads(candidate[start : end + 1])


def _prompt(transcript: str, metadata: dict[str, Any]) -> str:
    useful_metadata = {
        field: metadata.get(field)
        for field in ("id", "title", "uploader", "channel", "description", "webpage_url", "url")
        if metadata.get(field)
    }
    return f"""从下面的视频转写中提取塑料模型产品。只返回 JSON 数组，不要 Markdown。每个对象只能使用这些字段：{', '.join(CSV_FIELDS)}。模型名称是必填；无法确认的字段留空字符串，不要猜测。资料来源必须填写视频 URL。可以把产品规格、套件内容、发售备注放入详情。\n视频元数据：{json.dumps(useful_metadata, ensure_ascii=False)}\n视频转写：\n{transcript}"""


def extract_with_openai(transcript: str, metadata: dict[str, Any], model: str) -> list[dict[str, str]]:
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("LLM_API_KEY (or OPENAI_API_KEY) is required for --llm-provider openai")
    payload = json.dumps({"model": model, "temperature": 0, "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")), "messages": [{"role": "user", "content": _prompt(transcript, metadata)}]}).encode()
    base = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    base = base.rstrip("/")
    request = urllib.request.Request(base + "/chat/completions", data=payload, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read())
    content = result["choices"][0]["message"]["content"]
    return _json_from_text(content)


def fallback(metadata: dict[str, Any]) -> list[dict[str, str]]:
    title = metadata.get("title") or ""
    return [{field: (title if field == "模型名称" else metadata.get("url", "") if field == "资料来源" else "") for field in CSV_FIELDS}]


def write_csv(rows: list[dict[str, Any]], output: Path, source_url: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(rows, list):
        raise ValueError("product extraction must return a JSON array")
    if not rows:
        raise ValueError("product extraction returned no product rows")
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            normalized = {field: str(row.get(field) or "").strip() for field in CSV_FIELDS}
            normalized["资料来源"] = normalized["资料来源"] or source_url
            if not normalized["模型名称"]:
                raise ValueError("extracted row is missing required field: 模型名称")
            writer.writerow(normalized)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--llm-provider", choices=("openai", "none"), default=os.getenv("LLM_PROVIDER", "openai"))
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "Qwen3.5-35B-A3B"))
    args = parser.parse_args()
    transcript_payload = json.loads(args.transcript.read_text(encoding="utf-8"))
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    rows = extract_with_openai(transcript_payload.get("text", ""), metadata, args.model) if args.llm_provider == "openai" else fallback(metadata)
    write_csv(rows, args.output, metadata.get("webpage_url") or metadata.get("original_url") or metadata.get("url", ""))
    print(args.output)


if __name__ == "__main__":
    main()
