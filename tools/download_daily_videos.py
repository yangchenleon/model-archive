"""Download-only stage of the Daily Toy News pipeline (仅下载视频).

Fetches the UP space upload list, keeps at most one "daily news" video per
calendar day (scored with :mod:`tools.filter_daily_videos`), and stores only the
media + yt-dlp metadata, mirroring the existing ``outputs/daily_reports`` layout::

    outputs/daily_reports/<YYYYMMDD>_<BV ID>/
      video/<BV ID>.mp4
      video/<BV ID>.info.json

Audio extraction, ASR and LLM report generation are intentionally NOT performed
here; a later batch stage consumes these folders.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.download_bilibili import download
from tools.fetch_space_videos import fetch_space_videos
from tools.filter_daily_videos import group_and_select_daily_videos

REPORT_DIR_RE = re.compile(r"^(\d{8})_(BV[0-9A-Za-z]+)$")


def existing_reports(output_dir: Path) -> dict[str, dict[str, Path]]:
    """Map ``YYYYMMDD`` -> {video_id, folder} for folders already on disk."""
    found: dict[str, dict[str, Path]] = {}
    if not output_dir.is_dir():
        return found
    for child in sorted(output_dir.iterdir()):
        if not child.is_dir():
            continue
        match = REPORT_DIR_RE.match(child.name)
        if not match:
            continue
        found[match.group(1)] = {"video_id": match.group(2), "path": child}
    return found


def load_listing(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "videos" in data:
        data = data["videos"]
    return list(data)


def select_daily(entries: list[dict[str, Any]], start: str, end: str) -> dict[str, dict[str, Any]]:
    """Group entries by Beijing date and rank candidates with the existing heuristic."""
    grouped = group_and_select_daily_videos(entries, start_date=start, end_date=end)
    return grouped


def has_video(folder: Path) -> bool:
    video_dir = folder / "video"
    if not video_dir.is_dir():
        return False
    return any(p.suffix.lower() in {".mp4", ".mkv", ".webm", ".flv"} for p in video_dir.iterdir())


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def run(
    output_dir: Path,
    start_date: str,
    end_date: str,
    listing_file: Path | None = None,
    space_url: str = "https://space.bilibili.com/290901588/upload/video",
    max_items: int = 120,
    interval: float = 8.0,
    dry_run: bool = False,
    force: bool = False,
    manifest: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = existing_reports(output_dir)

    if listing_file and listing_file.exists():
        entries = load_listing(listing_file)
        print(f"📄 复用视频列表缓存: {listing_file} ({len(entries)} 条)")
    else:
        print(f"🔍 拉取 UP 空间视频列表 (最多 {max_items} 条)...")
        entries = fetch_space_videos(space_url, max_items=max_items)
        if listing_file:
            listing_file.parent.mkdir(parents=True, exist_ok=True)
            listing_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"💾 已缓存视频列表到: {listing_file}")

    selected = select_daily(entries, start_date, end_date)
    print(f"📅 目标区间 {start_date} ~ {end_date} 命中 {len(selected)} 天")

    results: list[dict[str, Any]] = []
    for day in sorted(selected):
        chosen = selected[day]["selected"]
        bvid = chosen["bvid"]
        folder_name = f"{day.replace('-', '')}_{bvid}"
        folder = output_dir / folder_name
        video_dir = folder / "video"

        day_key = day.replace("-", "")
        if day_key in existing:
            state = "skip-existing-report"
            print(f"⏭️  {day} 已有日报目录 {existing[day_key]['path'].name}，跳过")
            results.append({"date": day, "bvid": bvid, "status": state, "path": str(folder)})
            continue
        if has_video(folder) and not force:
            print(f"⏭️  {day} 视频已存在: {folder_name}")
            results.append({"date": day, "bvid": bvid, "status": "skip-existing-video", "path": str(folder)})
            continue

        print(
            f"⬇️  {day} {bvid} ({chosen.get('duration', 0)}s, score={chosen.get('news_score')}) "
            f"{chosen.get('title', '')[:40]}"
        )
        if dry_run:
            results.append({"date": day, "bvid": bvid, "status": "dry-run", "path": str(folder),
                            "candidates": selected[day]["candidates"]})
            continue

        video_dir.mkdir(parents=True, exist_ok=True)
        try:
            media = download(chosen["url"], video_dir)
            state = "downloaded"
            print(f"   ✅ {Path(media['media']).name} ({Path(media['media']).stat().st_size / 1e6:.1f} MB)")
        except Exception as exc:  # keep the batch alive, record the failure
            state = "failed"
            print(f"   ❌ 下载失败: {exc}")
            results.append({"date": day, "bvid": bvid, "status": state, "path": str(folder), "error": str(exc)})
            continue

        results.append(
            {
                "date": day,
                "bvid": bvid,
                "status": state,
                "path": str(folder),
                "duration": chosen.get("duration"),
                "news_score": chosen.get("news_score"),
                "title": chosen.get("title"),
                "candidates": selected[day]["candidates"],
            }
        )
        if interval:
            time.sleep(interval)

    summary = {
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(selected),
        "downloaded": sum(1 for r in results if r["status"] == "downloaded"),
        "skipped": sum(1 for r in results if r["status"].startswith("skip")),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "items": results,
    }
    if manifest:
        write_manifest(manifest, summary)
        print(f"🧾 清单已写入: {manifest}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_reports"))
    parser.add_argument("--space-url", default="https://space.bilibili.com/290901588/upload/video")
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD (Beijing date)")
    parser.add_argument("--end-date", default=datetime.date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--listing", type=Path, help="Cached space listing JSON (fetch when missing)")
    parser.add_argument("--max-items", type=int, default=120)
    parser.add_argument("--interval", type=float, default=8.0, help="Seconds between downloads")
    parser.add_argument("--manifest", type=Path, default=Path("outputs/daily_download_manifest.json"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    summary = run(
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        listing_file=args.listing,
        space_url=args.space_url,
        max_items=args.max_items,
        interval=args.interval,
        dry_run=args.dry_run,
        force=args.force,
        manifest=args.manifest,
    )
    print(
        f"\n=== 汇总: 下载 {summary['downloaded']} / 跳过 {summary['skipped']} / "
        f"失败 {summary['failed']} / 共 {summary['total_days']} 天 ==="
    )


if __name__ == "__main__":
    main()
