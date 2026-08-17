"""Run download -> audio extraction -> ASR -> CSV extraction as one job."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from tools.download_bilibili import download
from tools.extract_audio import extract
from tools.extract_products import extract_with_openai, fallback, write_csv
from tools.transcribe import transcribe


def safe_filename(value: str | None, fallback: str) -> str:
    """Make a title safe and portable as a filename without losing Chinese text."""
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", (value or "").strip())
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name or fallback)[:180]


def run(url: str, work_dir: Path, asr_provider: str, asr_model: str, llm_provider: str, llm_model: str, language: str | None, cookies: Path | None) -> dict[str, str]:
    video_dir = work_dir / "video"
    media = download(url, video_dir, cookies)
    audio_path = extract(Path(media["media"]), work_dir / "audio" / f"{media['video_id']}.wav")
    transcript = transcribe(audio_path, asr_provider, asr_model, language)
    transcript_path = work_dir / "transcript" / f"{media['video_id']}.json"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = json.loads(Path(media["metadata"]).read_text(encoding="utf-8"))
    title_stem = safe_filename(metadata.get("title") or media.get("title"), media["video_id"])
    text_path = work_dir / "transcript" / f"{title_stem}.txt"
    text_path.write_text(transcript.get("text", ""), encoding="utf-8")
    rows = extract_with_openai(transcript.get("text", ""), {**metadata, "url": url}, llm_model) if llm_provider == "openai" else fallback({**metadata, "url": url})
    csv_path = work_dir / "csv" / f"{title_stem}.csv"
    write_csv(rows, csv_path, url)
    return {"video_id": media["video_id"], "title": metadata.get("title") or media.get("title") or media["video_id"], "media": media["media"], "audio": str(audio_path), "transcript": str(transcript_path), "transcript_txt": str(text_path), "csv": str(csv_path)}


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
    args = parser.parse_args()
    print(json.dumps(run(args.url, args.work_dir, args.asr_provider, args.asr_model, args.llm_provider, args.llm_model, args.language, args.cookies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
