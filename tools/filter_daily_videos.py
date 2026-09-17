"""Atomic tool to filter and select Daily News videos by date and title density.

Given a list of UP space videos, this tool groups videos by date and identifies
the daily toy news report video (which typically features long, information-dense
titles mentioning multiple brands and models, separated by punctuation, with news keywords).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path
from typing import Any

from tools.fetch_space_videos import fetch_space_videos

NEWS_KEYWORDS = [
    "更新", "登场", "解禁", "跳水", "亮相", "上线", "发布", "登陆", "试模",
    "快讯", "钱包", "截击", "撞车", "背刺", "出货", "大货", "限定",
]


def score_news_title(title: str, duration: int) -> float:
    """Heuristic scoring for whether a video is a multi-product daily news roundup."""
    score = 0.0

    # Punctuation density (commas, exclamation marks, semicolons)
    segments = re.split(r"[,，!！;；、]", title)
    segments = [s.strip() for s in segments if len(s.strip()) >= 2]
    if len(segments) >= 4:
        score += 40.0
    elif len(segments) >= 2:
        score += 20.0

    # Keyword matching
    matched_keywords = [kw for kw in NEWS_KEYWORDS if kw in title]
    score += min(len(matched_keywords) * 10.0, 40.0)

    # Duration bonus: Daily news videos are typically 80s - 250s
    if 85 <= duration <= 300:
        score += 20.0
    elif duration > 300:
        score += 10.0
    elif duration < 60:
        score -= 20.0

    return score


def group_and_select_daily_videos(
    videos: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Group videos by date_str, filter by date range, and rank candidates."""
    by_date: dict[str, list[dict[str, Any]]] = {}
    for v in videos:
        d = v.get("date_str")
        if not d:
            continue
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        by_date.setdefault(d, []).append(v)

    results: dict[str, dict[str, Any]] = {}
    for d in sorted(by_date.keys()):
        candidates = by_date[d]
        ranked: list[dict[str, Any]] = []
        for cand in candidates:
            s = score_news_title(cand.get("title", ""), cand.get("duration", 0))
            cand_copy = dict(cand)
            cand_copy["news_score"] = round(s, 1)
            ranked.append(cand_copy)

        # Sort by score descending
        ranked.sort(key=lambda x: x["news_score"], reverse=True)
        results[d] = {
            "selected": ranked[0],
            "candidates": ranked,
        }

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space-url", default="https://space.bilibili.com/290901588/upload/video")
    parser.add_argument("--max-items", type=int, default=30)
    parser.add_argument("--start-date", help="Filter start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Filter end date (YYYY-MM-DD)")
    parser.add_argument("--last-week", action="store_true", help="Automatically select previous calendar week (Mon-Sun)")
    parser.add_argument("--output", type=Path, help="Save JSON mapping to file")
    args = parser.parse_args()

    start_date = args.start_date
    end_date = args.end_date

    if args.last_week:
        # Determine previous week (Monday to Sunday) relative to today or latest video
        today = datetime.date.today()
        # Find Monday of current week
        cur_monday = today - datetime.timedelta(days=today.weekday())
        last_sunday = cur_monday - datetime.timedelta(days=1)
        last_monday = last_sunday - datetime.timedelta(days=6)
        start_date = last_monday.strftime("%Y-%m-%d")
        end_date = last_sunday.strftime("%Y-%m-%d")
        print(f"Selecting last week: {start_date} ~ {end_date}")

    raw_videos = fetch_space_videos(args.space_url, max_items=args.max_items)
    selected_map = group_and_select_daily_videos(raw_videos, start_date=start_date, end_date=end_date)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(selected_map, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved selection mapping to {args.output}")

    print(f"\n=== 模玩日报视频筛选结果 (共 {len(selected_map)} 天) ===")
    for d, info in selected_map.items():
        sel = info["selected"]
        print(f"\n📅 【{d}】推荐速报 (得分: {sel['news_score']}):")
        print(f"   BV号: {sel['bvid']} ({sel['duration']}s)")
        print(f"   标题: {sel['title']}")
        if len(info["candidates"]) > 1:
            print("   同日其他候选视频:")
            for other in info["candidates"][1:]:
                print(f"     - {other['bvid']} ({other['duration']}s, 得分: {other['news_score']}): {other['title']}")


if __name__ == "__main__":
    main()
