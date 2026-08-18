"""Run download (when needed) -> distinct screenshot extraction for one video."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.download_bilibili import download
from tools.extract_screenshots import extract


def run(
    work_dir: Path,
    url: str | None = None,
    media: Path | None = None,
    interval: float = 1.0,
    threshold: float = 0.08,
    crop_top: float = 0.15,
    crop_bottom: float = 0.75,
    cookies: Path | None = None,
) -> dict:
    """Produce screenshot artifacts, downloading only if an existing media path is absent."""
    if media is None:
        if not url:
            raise ValueError("Pass a video URL or --media")
        downloaded = download(url, work_dir / "video", cookies)
        media = Path(downloaded["media"])
        video_id = downloaded["video_id"]
        title = downloaded.get("title")
    else:
        media = media.resolve()
        video_id = media.stem
        title = None
    result = extract(media, work_dir / "screenshots", interval, threshold, crop_top, crop_bottom)
    return {"video_id": video_id, "title": title, "media": str(media), **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", help="Bilibili video URL; omit when --media is supplied")
    parser.add_argument("--media", type=Path, help="Existing media file; skips download_bilibili")
    parser.add_argument("--work-dir", type=Path, default=Path("artifacts/screenshots"))
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.08)
    parser.add_argument("--crop-top", type=float, default=0.15)
    parser.add_argument("--crop-bottom", type=float, default=0.75)
    parser.add_argument("--cookies", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.work_dir, args.url, args.media, args.interval, args.threshold, args.crop_top, args.crop_bottom, args.cookies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
