"""Extract distinct screenshots from every locally downloaded video in a batch."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.screenshot_pipeline import run


MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".flv"}


def _jobs(work_dir: Path) -> list[tuple[str, Path, Path]]:
    """Return (video id, media path, per-video work directory) in stable order."""
    jobs: list[tuple[str, Path, Path]] = []
    for media in sorted((work_dir / "videos").glob("*/video/*")):
        if media.is_file() and media.suffix.lower() in MEDIA_SUFFIXES:
            jobs.append((media.parent.parent.name, media, media.parent.parent))
    if not jobs:
        raise RuntimeError(f"No downloaded video files found under {work_dir / 'videos'}")
    return jobs


def _write_summary(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def run_batch(
    work_dir: Path,
    interval: float = 1.0,
    threshold: float = 0.08,
    crop_top: float = 0.15,
    crop_bottom: float = 0.75,
    force: bool = False,
) -> dict:
    jobs = _jobs(work_dir)
    summary_path = work_dir / "batch" / "screenshot-summary.json"
    summary = {"work_dir": str(work_dir), "total": len(jobs), "completed": [], "skipped": [], "failed": []}
    for position, (video_id, media, video_work_dir) in enumerate(jobs, start=1):
        manifest = video_work_dir / "screenshots" / "manifest.json"
        base = {"position": position, "video_id": video_id, "media": str(media)}
        if manifest.exists() and not force:
            summary["skipped"].append({**base, "manifest": str(manifest)})
            _write_summary(summary_path, summary)
            print(json.dumps({**base, "status": "skipped"}, ensure_ascii=False), flush=True)
            continue
        try:
            result = run(video_work_dir, media=media, interval=interval, threshold=threshold, crop_top=crop_top, crop_bottom=crop_bottom)
            summary["completed"].append({**base, "screenshots_saved": result["screenshots_saved"], "manifest": result["manifest"]})
            status = "completed"
        except Exception as exc:  # Preserve enough state for the batch to continue and be reviewed.
            summary["failed"].append({**base, "error": str(exc)})
            status = "failed"
        _write_summary(summary_path, summary)
        print(json.dumps({**base, "status": status}, ensure_ascii=False), flush=True)
    return {**summary, "summary": str(summary_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="Existing batch directory containing videos/<BV ID>/video/")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.08)
    parser.add_argument("--crop-top", type=float, default=0.15)
    parser.add_argument("--crop-bottom", type=float, default=0.75)
    parser.add_argument("--force", action="store_true", help="Regenerate videos that already have screenshots/manifest.json")
    args = parser.parse_args()
    print(json.dumps(run_batch(args.work_dir, args.interval, args.threshold, args.crop_top, args.crop_bottom, args.force), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
