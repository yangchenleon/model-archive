"""Enumerate video URLs from a Bilibili season/list URL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.download_bilibili import _run, _yt_dlp


def list_videos(url: str, cookies_file: Path | None = None) -> list[dict[str, str]]:
    url = url.rstrip(",，")
    command = _yt_dlp() + ["--flat-playlist", "--dump-single-json", "--skip-download"]
    if cookies_file:
        command += ["--cookies", str(cookies_file)]
    payload = json.loads(_run(command + [url]).stdout)
    entries: list[dict[str, str]] = []
    for entry in payload.get("entries") or []:
        video_id = entry.get("id")
        if not video_id:
            continue
        entries.append({"video_id": video_id, "url": f"https://www.bilibili.com/video/{video_id}"})
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--cookies", type=Path)
    args = parser.parse_args()
    print(json.dumps(list_videos(args.url, args.cookies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
