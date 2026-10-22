"""Batch the ASR + daily-report stages over already downloaded videos.

Scans ``outputs/daily_reports/<YYYYMMDD>_<BV>/`` for folders that have the media
but no ``daily_report.json`` yet, then runs the audio -> ASR -> LLM chain for
each of them via :func:`tools.daily_pipeline.process_single_video`. The media is
reused from ``video/`` so nothing is downloaded again.

The run is resumable: a folder with ``daily_report.json`` is skipped, failures
are recorded and reported so a later retry only touches the broken days.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import time
from pathlib import Path
from typing import Any

from tools.config import load_env
from tools.daily_pipeline import process_single_video

REPORT_DIR_RE = re.compile(r"^(\d{8})_(BV[0-9A-Za-z]+)$")


def pending_reports(
    output_dir: Path,
    start: str | None = None,
    end: str | None = None,
) -> list[dict[str, Any]]:
    """Return report folders that still need a ``daily_report.json``."""
    items: list[dict[str, Any]] = []
    for path in sorted(output_dir.iterdir()):
        if not path.is_dir():
            continue
        match = REPORT_DIR_RE.match(path.name)
        if not match:
            continue
        day, bvid = match.group(1), match.group(2)
        if start and day < start:
            continue
        if end and day > end:
            continue
        if (path / "daily_report.json").exists():
            continue
        if not list((path / "video").glob("*.mp4")):
            continue
        items.append({"date": day, "bvid": bvid, "path": path})
    return items


def write_status(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/daily_reports"))
    parser.add_argument("--start-date", help="YYYYMMDD, inclusive")
    parser.add_argument("--end-date", help="YYYYMMDD, inclusive")
    parser.add_argument("--limit", type=int, help="Process at most N folders")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between videos")
    parser.add_argument("--force", action="store_true", help="Regenerate existing daily reports")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    items = pending_reports(args.output_dir, args.start_date, args.end_date)
    if args.limit:
        items = items[: args.limit]
    print(f"📋 待处理 {len(items)} 个视频", flush=True)
    if args.dry_run:
        for item in items:
            print(f"  {item['date']} {item['bvid']}", flush=True)
        return

    log_path = Path("outputs/daily_batch.log")
    status_path = Path("outputs/daily_batch_status.json")
    started_at = datetime.datetime.now().astimezone()
    results: list[dict[str, Any]] = []

    def log(message: str) -> None:
        stamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{stamp}] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    log(f"开始批处理: {len(items)} 个视频, 间隔 {args.interval}s")
    for index, item in enumerate(items, 1):
        day, bvid = item["date"], item["bvid"]
        t0 = time.time()
        log(f"[{index}/{len(items)}] {day} {bvid} 开始")
        try:
            result = process_single_video(
                f"https://www.bilibili.com/video/{bvid}",
                args.output_dir,
                force=args.force,
            )
            status = result.get("status", "completed")
            items_count = result.get("items_count")
            error = None
            log(f"[{index}/{len(items)}] {day} {bvid} {status} ({items_count} 条, {time.time() - t0:.0f}s)")
        except Exception as exc:  # keep the batch alive; failures are retried later
            status = "failed"
            items_count = None
            error = str(exc)[:500]
            log(f"[{index}/{len(items)}] {day} {bvid} FAILED: {error}")
        results.append({
            "date": day,
            "bvid": bvid,
            "status": status,
            "items_count": items_count,
            "error": error,
            "seconds": round(time.time() - t0, 1),
        })
        write_status(status_path, {
            "started_at": started_at.isoformat(timespec="seconds"),
            "updated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "total": len(items),
            "processed": len(results),
            "completed": sum(1 for r in results if r["status"] == "completed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "items": results,
        })
        if args.interval and index < len(items):
            time.sleep(args.interval)

    completed = sum(1 for r in results if r["status"] == "completed")
    failed = [r for r in results if r["status"] == "failed"]
    log(f"批处理结束: 成功 {completed}, 失败 {len(failed)}")
    for row in failed:
        log(f"  失败: {row['date']} {row['bvid']}: {row['error']}")


if __name__ == "__main__":
    main()
