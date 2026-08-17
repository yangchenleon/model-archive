"""Run the ingestion pipeline for every video in a Bilibili season/list."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tools.list_bilibili import list_videos
from tools.pipeline import run


def _replace_position(rows: list[dict], position: int, value: dict) -> list[dict]:
    return [row for row in rows if row.get("position") != position] + [value]


def run_batch(url: str, work_dir: Path, asr_provider: str, asr_model: str, llm_provider: str, llm_model: str, language: str | None, cookies: Path | None, start: int = 1, limit: int | None = None, retry: bool = False) -> dict:
    entries = list_videos(url, cookies)
    summary_path = work_dir / "batch" / "summary.json"
    existing = json.loads(summary_path.read_text(encoding="utf-8")) if retry and summary_path.exists() else None
    if retry:
        scope = set(range(start, len(entries) + 1))
        completed_positions = {row.get("position") for row in existing.get("completed", [])}
        failed_positions = {row.get("position") for row in existing.get("failed", [])}
        target_positions = sorted((failed_positions | (scope - completed_positions)) & scope)
        selected = [entries[position - 1] for position in target_positions]
        summary = existing
    else:
        selected = entries[start - 1 : (start - 1 + limit) if limit else None]
        target_positions = list(range(start, start + len(selected)))
        summary = {"source": url, "total": len(entries), "selected": len(selected), "completed": [], "failed": []}
    (work_dir / "batch").mkdir(parents=True, exist_ok=True)
    for position, entry in zip(target_positions, selected):
        video_dir = work_dir / "videos" / entry["video_id"]
        try:
            result = run(entry["url"], video_dir, asr_provider, asr_model, llm_provider, llm_model, language, cookies)
            summary["completed"] = _replace_position(summary["completed"], position, {"position": position, **result})
            summary["failed"] = [row for row in summary["failed"] if row.get("position") != position]
        except Exception as exc:  # Keep the batch moving; the summary is the retry queue.
            summary["failed"] = _replace_position(summary["failed"], position, {"position": position, **entry, "error": str(exc)})
            summary["completed"] = [row for row in summary["completed"] if row.get("position") != position]
        (work_dir / "batch" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        status = "completed" if any(row.get("position") == position for row in summary["completed"]) else "failed"
        print(json.dumps({"position": position, "total": len(entries), "status": status, "video_id": entry["video_id"]}, ensure_ascii=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--asr-provider", choices=("local", "openai", "compatible-chat"), default=os.getenv("ASR_PROVIDER", "local"))
    parser.add_argument("--asr-model", default=os.getenv("WHISPER_MODEL", "small"))
    parser.add_argument("--llm-provider", choices=("openai", "none"), default=os.getenv("LLM_PROVIDER", "openai"))
    parser.add_argument("--llm-model", default=os.getenv("LLM_MODEL", "Qwen3.5-35B-A3B"))
    parser.add_argument("--language", default=os.getenv("ASR_LANGUAGE", "zh"))
    parser.add_argument("--cookies", type=Path)
    parser.add_argument("--start", type=int, default=1, help="1-based entry number for resume/retry")
    parser.add_argument("--limit", type=int, help="Only process this many entries")
    parser.add_argument("--retry", action="store_true", help="Retry failed and pending entries in the --start..end range")
    args = parser.parse_args()
    summary = run_batch(args.url, args.work_dir, args.asr_provider, args.asr_model, args.llm_provider, args.llm_model, args.language, args.cookies, args.start, args.limit, args.retry)
    print(json.dumps({"total": summary["total"], "completed": len(summary["completed"]), "failed": len(summary["failed"]), "summary": str(args.work_dir / "batch" / "summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
