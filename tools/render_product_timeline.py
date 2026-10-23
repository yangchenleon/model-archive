"""Render aligned product mentions as a self-contained HTML timeline."""
from __future__ import annotations

import argparse
import datetime
import html
import json
from pathlib import Path
from typing import Any

STAGE_COLORS = {
    "rumor": "#8a8f98",
    "teaser": "#8b5cf6",
    "announced": "#2563eb",
    "preorder": "#d97706",
    "released": "#16a34a",
    "reprint": "#0d9488",
    "discontinued": "#dc2626",
    "unknown": "#6b7280",
}
STAGE_LABELS = {
    "rumor": "传闻", "teaser": "预告", "announced": "公布", "preorder": "预售",
    "released": "现货", "reprint": "再版", "discontinued": "停产", "unknown": "未知",
}


def parse_date(value: str) -> datetime.date:
    return datetime.date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def stage_dot(entry: dict[str, Any]) -> str:
    color = STAGE_COLORS.get(entry["stage"], "#6b7280")
    label = STAGE_LABELS.get(entry["stage"], entry["stage"])
    tip = html.escape(
        f"{entry['date']} {label}"
        + (f" · {entry['event']}" if entry.get("event") not in (None, "none") else "")
        + (f" · {entry['price']}元" if entry.get("price") else "")
        + (f"\n{entry['evidence']}" if entry.get("evidence") else "")
    )
    link = (
        f'<a href="https://www.bilibili.com/video/{entry["video_id"]}?t={int(entry["start"])}" target="_blank" '
        f'style="background:{color}" title="{tip}"></a>'
        if entry.get("video_id") and entry.get("start") is not None
        else f'<span style="background:{color}" title="{tip}"></span>'
    )
    return link


def render(products: list[dict[str, Any]], review: list[dict[str, Any]], title: str, min_mentions: int = 2) -> str:
    all_dates = [parse_date(e["date"]) for p in products for e in p["timeline"]]
    start, end = (min(all_dates), max(all_dates)) if all_dates else (datetime.date.today(), datetime.date.today())
    span = max(1, (end - start).days)
    multi = [p for p in products if p["mention_count"] > 1]
    mentions = sum(p["mention_count"] for p in products)

    rows = []
    for product in sorted(products, key=lambda p: (-p["mention_count"], p["brand"], p["model_name"])):
        if product["mention_count"] < min_mentions:
            continue
        dots = []
        for entry in product["timeline"]:
            day = parse_date(entry["date"])
            left = (day - start).days / span * 100
            dots.append(
                f'<div class="marker" style="left:{left:.2f}%">{stage_dot(entry)}</div>'
            )
        rows.append(
            f"""
        <div class="product">
          <div class="meta">
            <strong>{html.escape(product['brand'])} · {html.escape(product['model_name'])}</strong>
            <span class="stage" style="color:{STAGE_COLORS.get(product['current_stage'], '#666')}">
              {STAGE_LABELS.get(product['current_stage'], product['current_stage'])}
            </span>
            <span class="count">×{product['mention_count']}</span>
          </div>
          <div class="track">{''.join(dots)}</div>
        </div>"""
        )

    legend = "".join(
        f'<span class="legend-item"><i style="background:{color}"></i>{STAGE_LABELS[stage]}</span>'
        for stage, color in STAGE_COLORS.items()
    )
    review_rows = "".join(
        f"<li>{html.escape(item['left'].get('brand', ''))} {html.escape(item['left'].get('name', ''))} "
        f"~ {html.escape(item['right'].get('name', ''))}（相似度 {item['score']}）</li>"
        for item in review[:30]
    )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 24px; background:#fafafa; color:#111; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color:#666; font-size: 13px; margin-bottom: 16px; }}
  .legend {{ margin: 8px 0 20px; font-size: 12px; color:#444; }}
  .legend-item {{ margin-right: 14px; }}
  .legend-item i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }}
  .product {{ margin-bottom: 14px; }}
  .meta {{ font-size: 13px; margin-bottom: 4px; }}
  .meta .stage {{ margin-left: 8px; font-size: 12px; font-weight: 600; }}
  .meta .count {{ margin-left: 6px; color:#888; font-size: 12px; }}
  .track {{ position: relative; height: 26px; background: linear-gradient(#eee,#eee) center/100% 2px no-repeat; }}
  .marker {{ position:absolute; top: 0; transform: translateX(-50%); }}
  .marker a, .marker span {{ display:block; width:14px; height:14px; border-radius:50%; border:2px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,.25); margin-top:5px; }}
  .review {{ margin-top: 28px; font-size: 13px; }}
  .review li {{ margin-bottom: 4px; }}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">产品 {len(products)} 个 · mention {mentions} 条 · 多提及产品 {len(multi)} 个 · 时间范围 {start} ~ {end}</div>
<div class="legend">{legend}</div>
{''.join(rows) or '<p>没有跨天重复的产品。</p>'}
<div class="review"><h2 style="font-size:15px">待人工复核（{len(review)}）</h2><ul>{review_rows or '<li>无</li>'}</ul></div>
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, default=Path("outputs/daily_v2/products.json"))
    parser.add_argument("--review", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("outputs/daily_v2/timeline.html"))
    parser.add_argument("--title", default="模玩速报 · 产品时间线")
    parser.add_argument("--min-mentions", type=int, default=2, help="Only render products with at least N mentions")
    args = parser.parse_args()

    products = json.loads(args.products.read_text(encoding="utf-8"))
    review_path = args.review or args.products.with_name("review.json")
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(products, review, args.title, args.min_mentions), encoding="utf-8")
    print(f"written {args.output} ({len(products)} products)")


if __name__ == "__main__":
    main()
