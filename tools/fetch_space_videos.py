"""Atomic tool to fetch and paginate video submissions from a Bilibili UP space.

Features:
- Automatically handles buvid3/buvid4 cookie generation to bypass Bilibili 412/352 blocking.
- Fetches chronological video IDs using yt-dlp flat playlist.
- Concurrently/quickly resolves video details (title, pubdate, duration, desc) via public API.
- Returns structured video entries grouped or filterable by date.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from tools.download_bilibili import _yt_dlp

COOKIE_CACHE_FILE = Path("/tmp/bilibili_space_cookie.txt")


def fetch_buvid() -> tuple[str, str]:
    """Retrieve buvid3 and buvid4 from Bilibili's public finger SPI endpoint."""
    url = "https://api.bilibili.com/x/frontend/finger/spi"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    b3 = data.get("data", {}).get("b_3", "")
    b4 = data.get("data", {}).get("b_4", "")
    return b3, b4


def get_or_create_cookie_file(force_refresh: bool = False) -> Path:
    """Provide a valid Netscape cookie file containing buvid tokens."""
    if not force_refresh and COOKIE_CACHE_FILE.exists():
        # Check if modified within 1 day
        mtime = COOKIE_CACHE_FILE.stat().st_mtime
        if time.time() - mtime < 86400:
            return COOKIE_CACHE_FILE

    b3, b4 = fetch_buvid()
    lines = [
        "# Netscape HTTP Cookie File",
        f".bilibili.com\tTRUE\t/\tFALSE\t2147483647\tbuvid3\t{b3}",
        f".bilibili.com\tTRUE\t/\tFALSE\t2147483647\tbuvid4\t{b4}",
        f".bilibili.com\tTRUE\t/\tFALSE\t2147483647\tb_nut\t{int(time.time())}",
    ]
    COOKIE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_CACHE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return COOKIE_CACHE_FILE


def normalize_space_url(url: str) -> str:
    cleaned = url.rstrip(",，/ ")
    match = re.search(r"space\.bilibili\.com/(\d+)", cleaned)
    if match:
        mid = match.group(1)
        return f"https://space.bilibili.com/{mid}/upload/video"
    return cleaned


def fetch_video_detail(bvid: str) -> dict[str, Any]:
    """Fetch video metadata directly from Bilibili's public view API."""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    
    vd = res.get("data", {})
    pubdate = vd.get("pubdate", 0)
    dt = datetime.datetime.fromtimestamp(pubdate) if pubdate else datetime.datetime.now()
    return {
        "bvid": bvid,
        "url": f"https://www.bilibili.com/video/{bvid}",
        "title": vd.get("title", ""),
        "date_str": dt.strftime("%Y-%m-%d"),
        "datetime_str": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": pubdate,
        "duration": vd.get("duration", 0),
        "desc": vd.get("desc", ""),
        "pic": vd.get("pic", ""),
    }


def fetch_space_videos(
    space_url: str = "https://space.bilibili.com/290901588/upload/video",
    max_items: int = 30,
    page_size: int = 30,
) -> list[dict[str, Any]]:
    """Fetch recent chronological videos from UP space with pagination and metadata."""
    url = normalize_space_url(space_url)
    cookie_file = get_or_create_cookie_file()

    bvids: list[str] = []
    current_start = 1

    while len(bvids) < max_items:
        if current_start > 1:
            time.sleep(2.5)
        current_end = current_start + page_size - 1
        cmd = _yt_dlp() + [
            "--flat-playlist",
            "--dump-single-json",
            "--skip-download",
            "--sleep-requests", "2.5",
            "--playlist-start", str(current_start),
            "--playlist-end", str(current_end),
            "--cookies", str(cookie_file),
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36",
            "--referer", "https://www.bilibili.com",
            url,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # If cookie expired, retry once with fresh cookie
            cookie_file = get_or_create_cookie_file(force_refresh=True)
            cmd[cmd.index(str(COOKIE_CACHE_FILE))] = str(cookie_file)
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Warning: yt-dlp pagination failed at {current_start}-{current_end}: {res.stderr[:200]}", file=sys.stderr)
                break

        payload = json.loads(res.stdout)
        entries = payload.get("entries") or []
        if not entries:
            break

        new_bvids = [e["id"] for e in entries if e.get("id") and e["id"] not in bvids]
        if not new_bvids:
            break

        bvids.extend(new_bvids)
        current_start += page_size

        if len(entries) < page_size:
            break

    target_bvids = bvids[:max_items]
    results: list[dict[str, Any]] = []
    for vid in target_bvids:
        try:
            info = fetch_video_detail(vid)
            results.append(info)
        except Exception as exc:
            print(f"Warning: Failed to fetch view details for {vid}: {exc}", file=sys.stderr)
            results.append({
                "bvid": vid,
                "url": f"https://www.bilibili.com/video/{vid}",
                "title": "",
                "date_str": "",
                "datetime_str": "",
                "timestamp": 0,
                "duration": 0,
                "desc": "",
                "pic": "",
            })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("space_url", nargs="?", default="https://space.bilibili.com/290901588/upload/video")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum number of videos to fetch")
    parser.add_argument("--output", type=Path, help="Optional JSON file to save video list")
    args = parser.parse_args()

    videos = fetch_space_videos(args.space_url, max_items=args.max_items)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(videos)} videos to {args.output}")
    else:
        print(f"=== UP主最新投稿视频列表 (共 {len(videos)} 条) ===")
        for idx, v in enumerate(videos, 1):
            print(f"[{idx:02d}] {v['datetime_str']} | {v['bvid']} ({v['duration']}s) | {v['title']}")


if __name__ == "__main__":
    main()
