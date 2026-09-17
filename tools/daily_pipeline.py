"""End-to-end Daily Toy News Pipeline (模玩日报系统流水线).

Supports processing single Bilibili videos or fetching the latest video(s)
from a Bilibili UP space URL (e.g. https://space.bilibili.com/290901588).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any

from tools.config import load_env
from tools.download_bilibili import _run, _yt_dlp, download
from tools.extract_audio import extract
from tools.extract_daily_news import extract_daily_news
from tools.transcribe import transcribe

load_env()


def get_beijing_date_str(metadata: dict[str, Any], fmt: str = "%Y%m%d") -> str:
    """Format release timestamp in China Standard Time (UTC+8) to avoid UTC day shift."""
    ts = metadata.get("timestamp") or metadata.get("pubdate")
    if ts:
        tz_bj = datetime.timezone(datetime.timedelta(hours=8))
        return datetime.datetime.fromtimestamp(ts, tz_bj).strftime(fmt)
    raw = metadata.get("upload_date") or ""
    if fmt == "%Y-%m-%d" and len(raw) == 8:
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw or "unknown_date"


def is_space_url(url: str) -> bool:
    return "space.bilibili.com" in url


def normalize_space_url(url: str) -> str:
    """Ensure UP space URL points to the chronological video upload page (/upload/video)."""
    cleaned = url.rstrip(",，/ ")
    match = re.search(r"space\.bilibili\.com/(\d+)", cleaned)
    if match:
        mid = match.group(1)
        return f"https://space.bilibili.com/{mid}/upload/video"
    return cleaned


def get_latest_videos_from_space(space_url: str, limit: int = 1) -> list[dict[str, str]]:
    """Query Bilibili UP space video uploads and return the top `limit` video entries."""
    url = normalize_space_url(space_url)
    # Bilibili space video API requires minimum page size (at least 5 items),
    # otherwise it responds with HTTP 412. We fetch at least 5 and slice entries[:limit].
    fetch_count = max(5, limit)
    command = _yt_dlp() + [
        "--flat-playlist",
        "--dump-single-json",
        "--skip-download",
        "--playlist-items",
        f"1:{fetch_count}",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "--referer",
        "https://www.bilibili.com",
        url,
    ]
    try:
        result = _run(command)
    except RuntimeError as exc:
        err_msg = str(exc)
        if "352" in err_msg or "412" in err_msg or "blocked by server" in err_msg:
            raise RuntimeError(
                f"Bilibili 个人空间列表接口触发了风控限制 (352/412)。\n"
                f"解决方案：\n"
                f"1. 建议直接传入视频链接（如：https://www.bilibili.com/video/BV1tAeN6LETP）；\n"
                f"2. 或通过 `--cookies /path/to/cookies.txt` 携带登录凭证运行。"
            ) from exc
        raise
    payload = json.loads(result.stdout)
    entries: list[dict[str, str]] = []
    for item in payload.get("entries") or []:
        vid = item.get("id")
        if not vid:
            continue
        entries.append({
            "video_id": vid,
            "url": f"https://www.bilibili.com/video/{vid}",
            "title": item.get("title") or "",
        })
    return entries[:limit]


def process_single_video(
    url: str,
    output_base_dir: Path,
    asr_model: str = "qwen3-asr-flash",
    language: str = "zh",
    llm_model: str | None = None,
    force: bool = False,
    cookies_file: Path | None = None,
) -> dict[str, Any]:
    """Execute download -> audio -> ASR -> daily news extraction for one video."""
    # First inspect/extract basic video ID from URL
    match = re.search(r"(BV[0-9A-Za-z]+)", url)
    video_id_hint = match.group(1) if match else "video"

    temp_video_dir = output_base_dir / "_temp" / video_id_hint / "video"
    print(f"\n[1/4] 获取视频与元数据: {url}")
    media = download(url, temp_video_dir, cookies_file=cookies_file)
    video_id = media["video_id"]
    metadata_path = Path(media["metadata"])
    metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))

    upload_date = get_beijing_date_str(metadata)
    folder_name = f"{upload_date}_{video_id}"
    report_dir = output_base_dir / folder_name

    json_report = report_dir / "daily_report.json"

    if not force and json_report.exists():
        print(f"ℹ️ 该视频日报已存在，跳过处理（如需重新生成请加 --force）: {report_dir}")
        data = json.loads(json_report.read_text(encoding="utf-8"))
        return {
            "video_id": video_id,
            "title": metadata.get("title"),
            "report_title": data.get("report_title"),
            "items_count": len(data.get("news_items", [])),
            "report_dir": str(report_dir),
            "json_path": str(json_report),
            "status": "cached",
        }

    report_dir.mkdir(parents=True, exist_ok=True)

    # Move media & metadata to target report dir
    target_video_dir = report_dir / "video"
    target_video_dir.mkdir(parents=True, exist_ok=True)
    target_metadata = target_video_dir / f"{video_id}.info.json"
    target_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Extract audio
    print(f"[2/4] 提取标准化音频 (16kHz WAV)...")
    audio_dir = report_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_path = audio_dir / f"{video_id}.wav"
    extract(Path(media["media"]), wav_path)

    # 3. Transcribe audio
    print(f"[3/4] 语音识别转写 ASR (模型: {asr_model})...")
    transcript_payload = transcribe(wav_path, model_name=asr_model, language=language)
    transcript_text = transcript_payload.get("text", "").strip()

    trans_dir = report_dir / "transcript"
    trans_dir.mkdir(parents=True, exist_ok=True)
    (trans_dir / f"{video_id}.json").write_text(
        json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (trans_dir / f"{video_id}.txt").write_text(transcript_text, encoding="utf-8")
    print(f"  ASR 完成，识别出 {len(transcript_text)} 字。")

    # 4. Extract Daily News
    print(f"[4/4] 大模型纠偏与结构化日报生成...")
    result = extract_daily_news(transcript_text, metadata, report_dir, model_override=llm_model)
    report_data = result["report_data"]

    items_count = len(report_data.get("news_items", []))
    print(f"✅ 日报生成成功！提炼出 {items_count} 款模玩情报。")
    print(f"  - 结构化 JSON: {result['json_path']} (含ASR原文及元数据)")

    return {
        "video_id": video_id,
        "title": metadata.get("title"),
        "report_title": report_data.get("report_title"),
        "items_count": items_count,
        "report_dir": str(report_dir),
        "json_path": result["json_path"],
        "status": "completed",
    }


def run_pipeline(
    target: str,
    output_base_dir: Path,
    limit: int = 1,
    asr_model: str = "qwen3-asr-flash",
    language: str = "zh",
    llm_model: str | None = None,
    force: bool = False,
    cookies_file: Path | None = None,
) -> list[dict[str, Any]]:
    output_base_dir.mkdir(parents=True, exist_ok=True)

    if is_space_url(target):
        print(f"🔍 检测到 Bilibili UP 主空间地址: {target}")
        print(f"正在获取最新发布的前 {limit} 个视频...")
        videos = get_latest_videos_from_space(target, limit=limit)
        if not videos:
            print("❌ 未在 UP 空间中找到任何视频。")
            return []
        print(f"共定位到 {len(videos)} 个视频:")
        for idx, v in enumerate(videos, 1):
            print(f"  [{idx}] {v['video_id']} - {v['url']}")
    else:
        videos = [{"video_id": "", "url": target, "title": ""}]

    results: list[dict[str, Any]] = []
    for item in videos:
        res = process_single_video(
            item["url"],
            output_base_dir=output_base_dir,
            asr_model=asr_model,
            language=language,
            llm_model=llm_model,
            force=force,
            cookies_file=cookies_file,
        )
        results.append(res)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Bilibili video URL, BV ID, or UP Space URL (e.g. https://space.bilibili.com/290901588)")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_reports"), help="Output directory")
    parser.add_argument("--limit", type=int, default=1, help="Number of latest videos to fetch if target is space URL (default: 1)")
    parser.add_argument("--asr-model", default="qwen3-asr-flash", help="ASR model name")
    parser.add_argument("--language", default="zh", help="ASR language code")
    parser.add_argument("--llm-model", default=None, help="LLM model override")
    parser.add_argument("--force", action="store_true", help="Force regenerate even if already exists")
    parser.add_argument("--cookies", type=Path, help="Path to Netscape cookies file")

    args = parser.parse_args()
    results = run_pipeline(
        args.target,
        output_base_dir=args.output_dir,
        limit=args.limit,
        asr_model=args.asr_model,
        language=args.language,
        llm_model=args.llm_model,
        force=args.force,
        cookies_file=args.cookies,
    )
    print("\n=== 执行报告摘要 ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
