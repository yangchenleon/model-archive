"""Download a Bilibili video and persist its extractor metadata.

This tool deliberately shells out to yt-dlp so it can use the latest extractor
without coupling the project to yt-dlp's Python API. Install yt-dlp and ffmpeg
on the host (or provide a yt-dlp executable in PATH).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


def _yt_dlp() -> list[str]:
    executable = shutil.which("yt-dlp")
    if executable:
        return [executable]
    if importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    raise RuntimeError(
        "yt-dlp is unavailable. Install it with "
        "`python3 -m pip install -r tools/requirements.txt`."
    )


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"yt-dlp failed: {detail[-4000:]}") from exc


def download(url: str, output_dir: Path, cookies_file: Path | None = None) -> dict:
    url = url.rstrip(",，")
    output_dir.mkdir(parents=True, exist_ok=True)
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg is required to merge Bilibili video/audio streams. "
            "Install ffmpeg before running the pipeline."
        )
    common = _yt_dlp() + ["--no-playlist", "--newline"]
    if cookies_file:
        common += ["--cookies", str(cookies_file)]

    metadata_result = _run(common + ["--dump-single-json", "--skip-download", url])
    metadata = json.loads(metadata_result.stdout)
    video_id = metadata.get("id") or "video"
    metadata_path = output_dir / f"{video_id}.info.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    template = str(output_dir / f"{video_id}.%(ext)s")
    _run(common + ["-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", template, url])
    candidates = sorted(
        path for path in output_dir.glob(f"{video_id}.*")
        if path.suffix.lower() not in {".json", ".part", ".ytdl"}
    )
    media = output_dir / f"{video_id}.mp4"
    if not media.exists():
        media = next((path for path in candidates if path.suffix.lower() in {".mkv", ".webm", ".flv"}), None)
    if media is None:
        raise RuntimeError(f"yt-dlp completed but no media file was found in {output_dir}")
    return {"url": url, "video_id": video_id, "title": metadata.get("title"), "media": str(media), "metadata": str(metadata_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/video"))
    parser.add_argument("--cookies", type=Path, help="Optional Netscape cookies file for login-only videos")
    args = parser.parse_args()
    print(json.dumps(download(args.url, args.output_dir, args.cookies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
