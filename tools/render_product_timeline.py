"""Render aligned product mentions as a self-contained HTML catalog.

Every product is one collapsed entry; expanding it lists the individual mentions
(date, stage, price, variant, verbatim quote) with a deep link back to the video
second. A search box and a multi-mention filter make the full catalog usable.
"""
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
EVENT_LABELS = {
    "price_change": "价格变动", "delay": "延期", "review": "测评", "accessory": "配件", "none": "",
}


def parse_date(value: str) -> datetime.date:
    return datetime.date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def bilibili_link(entry: dict[str, Any]) -> str:
    if not entry.get("video_id") or entry.get("start") is None:
        return ""
    start = int(entry["start"])
    stamp = f"{start // 60}:{start % 60:02d}"
    url = f"https://www.bilibili.com/video/{entry['video_id']}?t={start}"
    return f'<a class="src" href="{url}" target="_blank" rel="noopener">{stamp} ▶</a>'


def mention_row(entry: dict[str, Any]) -> str:
    stage = entry["stage"]
    label = STAGE_LABELS.get(stage, stage)
    event = EVENT_LABELS.get(entry.get("event", "none"), "")
    stage_html = f'<span class="chip" style="--c:{STAGE_COLORS.get(stage, "#6b7280")}">{label}</span>'
    if event:
        stage_html += f' <span class="event">{event}</span>'
    return (
        f"<tr>"
        f'<td class="date">{html.escape(entry["date"])}</td>'
        f"<td>{stage_html}</td>"
        f'<td class="price">{html.escape(entry.get("price") or "")}</td>'
        f'<td class="variant">{html.escape(entry.get("variant") or "")}</td>'
        f'<td class="quote">{html.escape(entry.get("evidence") or "")}</td>'
        f'<td class="link">{bilibili_link(entry)}</td>'
        f"</tr>"
    )


def product_entry(product: dict[str, Any]) -> str:
    count = product["mention_count"]
    stage = product["current_stage"]
    label = STAGE_LABELS.get(stage, stage)
    variants = [v for v in product["variants"] if v]
    variant_html = "".join(f'<span class="variant-chip">{html.escape(v)}</span>' for v in variants)
    latest = product["timeline"][-1]["date"] if product["timeline"] else ""
    rows = "".join(mention_row(entry) for entry in product["timeline"])
    return f"""
<details class="product" data-count="{count}" data-stage="{stage}">
  <summary>
    <span class="dot" style="background:{STAGE_COLORS.get(stage, '#6b7280')}"></span>
    <span class="brand">{html.escape(product['brand'])}</span>
    <span class="name">{html.escape(product['model_name'])}</span>
    <span class="count">×{count}</span>
    <span class="stage">{label}</span>
    <span class="variants">{variant_html}</span>
    <span class="latest">{latest}</span>
  </summary>
  <div class="mentions">
    <table>
      <thead><tr><th>日期</th><th>阶段</th><th>价格</th><th>版本</th><th>原文</th><th>链接</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</details>"""


def render(products: list[dict[str, Any]], review: list[dict[str, Any]], title: str, min_mentions: int = 1) -> str:
    shown = [product for product in products if product["mention_count"] >= min_mentions]
    dates = [parse_date(entry["date"]) for product in shown for entry in product["timeline"]]
    start, end = (min(dates), max(dates)) if dates else (datetime.date.today(), datetime.date.today())
    mentions = sum(product["mention_count"] for product in shown)
    multi = sum(1 for product in shown if product["mention_count"] > 1)
    entries = "\n".join(
        product_entry(product)
        for product in sorted(shown, key=lambda p: (-p["mention_count"], p["brand"], p["model_name"]))
    )
    legend = "".join(
        f'<span class="legend-item"><i style="background:{color}"></i>{STAGE_LABELS[stage]}</span>'
        for stage, color in STAGE_COLORS.items()
    )
    review_rows = "".join(
        f'<li><span class="r-brand">{html.escape(item["left"].get("brand", ""))}</span> '
        f'{html.escape(item["left"].get("name", ""))} <span class="r-sep">~</span> '
        f'{html.escape(item["right"].get("name", ""))} <span class="r-score">{item["score"]}</span></li>'
        for item in review[:200]
    )

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ --line:#e5e7eb; --muted:#6b7280; --bg:#f7f7f8; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; background:var(--bg); color:#111; }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 60px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  .sub {{ color:var(--muted); font-size: 13px; }}
  .toolbar {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:18px 0 10px; }}
  .toolbar input[type=search] {{ flex:1 1 260px; min-width:220px; padding:9px 12px; border:1px solid var(--line); border-radius:8px; font-size:14px; background:#fff; }}
  .toolbar button {{ padding:8px 12px; border:1px solid var(--line); background:#fff; border-radius:8px; font-size:13px; cursor:pointer; }}
  .toolbar label {{ font-size:13px; color:#374151; display:flex; gap:6px; align-items:center; }}
  .legend {{ font-size:12px; color:#444; margin: 4px 0 18px; }}
  .legend-item {{ margin-right:14px; }}
  .legend-item i {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; }}
  details.product {{ background:#fff; border:1px solid var(--line); border-radius:10px; margin-bottom:8px; }}
  details.product > summary {{ list-style:none; cursor:pointer; padding:11px 14px; display:flex; align-items:center; gap:9px; flex-wrap:wrap; }}
  details.product > summary::-webkit-details-marker {{ display:none; }}
  details.product[open] > summary {{ border-bottom:1px solid var(--line); }}
  .dot {{ width:9px; height:9px; border-radius:50%; flex:0 0 auto; }}
  .brand {{ font-weight:600; font-size:14px; }}
  .name {{ font-size:14px; }}
  .count {{ font-size:12px; color:var(--muted); }}
  .stage {{ font-size:12px; color:#374151; background:#f3f4f6; border-radius:999px; padding:1px 8px; }}
  .variants {{ display:flex; gap:4px; flex-wrap:wrap; }}
  .variant-chip {{ font-size:11px; color:#4b5563; border:1px solid var(--line); border-radius:999px; padding:1px 7px; }}
  .latest {{ margin-left:auto; font-size:12px; color:var(--muted); font-variant-numeric: tabular-nums; }}
  .mentions {{ padding: 2px 14px 12px; overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; table-layout:fixed; }}
  th, td {{ overflow-wrap:anywhere; }}
  th:nth-child(1), td:nth-child(1) {{ width:88px; }}
  th:nth-child(2), td:nth-child(2) {{ width:104px; }}
  th:nth-child(3), td:nth-child(3) {{ width:74px; }}
  th:nth-child(4), td:nth-child(4) {{ width:112px; }}
  th:nth-child(6), td:nth-child(6) {{ width:72px; }}
  th {{ text-align:left; font-weight:500; color:var(--muted); font-size:12px; padding:10px 6px 6px; border-bottom:1px solid var(--line); }}
  td {{ padding:8px 6px; border-bottom:1px solid #f1f2f4; vertical-align:top; }}
  td.date {{ white-space:nowrap; font-variant-numeric: tabular-nums; color:#374151; }}
  td.price {{ white-space:nowrap; }}
  td.variant {{ white-space:nowrap; color:#4b5563; }}
  td.quote {{ color:#374151; }}
  .chip {{ font-size:11px; color:var(--c); border:1px solid color-mix(in srgb, var(--c) 40%, white); background:color-mix(in srgb, var(--c) 8%, white); border-radius:999px; padding:1px 8px; white-space:nowrap; }}
  .event {{ font-size:11px; color:var(--muted); }}
  .src {{ color:#2563eb; text-decoration:none; white-space:nowrap; font-variant-numeric: tabular-nums; }}
  .src:hover {{ text-decoration:underline; }}
  .empty {{ padding:40px 0; color:var(--muted); text-align:center; }}
  details.review {{ margin-top:26px; background:#fff; border:1px solid var(--line); border-radius:10px; padding: 4px 16px 12px; }}
  details.review summary {{ cursor:pointer; font-size:14px; font-weight:600; padding:10px 0; }}
  details.review ul {{ margin:6px 0 0; padding-left:18px; font-size:13px; }}
  details.review li {{ margin-bottom:5px; }}
  .r-brand {{ font-weight:600; }}
  .r-sep {{ color:#9ca3af; margin:0 2px; }}
  .r-score {{ color:var(--muted); font-size:11px; }}
  @media (max-width: 720px) {{
    .latest {{ margin-left:0; width:100%; }}
    td.quote {{ min-width:220px; }}
  }}
</style></head><body>
<div class="wrap">
<h1>{html.escape(title)}</h1>
<div class="sub">产品 {len(shown)} 个 · mention {mentions} 条 · 多提及产品 {multi} 个 · 时间范围 {start} ~ {end} · 点击条目展开明细</div>
<div class="legend">{legend}</div>

<div class="toolbar">
  <input type="search" id="q" placeholder="搜索品牌 / 产品 / 版本 / 原文片段…">
  <label><input type="checkbox" id="multiOnly"> 只看多提及</label>
  <button id="expandAll">全部展开</button>
  <button id="collapseAll">全部收起</button>
</div>

<div id="list">
{entries or '<div class="empty">没有产品。</div>'}
</div>

<details class="review">
  <summary>待人工复核（{len(review)} 对）</summary>
  <ul>{review_rows or '<li>无</li>'}</ul>
</details>
</div>
<script>
(function () {{
  var q = document.getElementById('q');
  var multi = document.getElementById('multiOnly');
  var list = document.getElementById('list');
  function apply() {{
    var term = (q.value || '').trim().toLowerCase();
    list.querySelectorAll('details.product').forEach(function (el) {{
      var hitTerm = !term || el.textContent.toLowerCase().indexOf(term) >= 0;
      var hitMulti = !multi.checked || Number(el.dataset.count) > 1;
      el.style.display = (hitTerm && hitMulti) ? '' : 'none';
    }});
  }}
  q.addEventListener('input', apply);
  multi.addEventListener('change', apply);
  document.getElementById('expandAll').addEventListener('click', function () {{
    list.querySelectorAll('details.product').forEach(function (el) {{ if (el.style.display !== 'none') el.open = true; }});
  }});
  document.getElementById('collapseAll').addEventListener('click', function () {{
    list.querySelectorAll('details.product').forEach(function (el) {{ el.open = false; }});
  }});
}})();
</script>
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", type=Path, default=Path("outputs/products/products.json"))
    parser.add_argument("--review", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("outputs/products/timeline.html"))
    parser.add_argument("--title", default="模玩速报 · 产品目录")
    parser.add_argument("--min-mentions", type=int, default=1, help="Only render products with at least N mentions")
    args = parser.parse_args()

    products = json.loads(args.products.read_text(encoding="utf-8"))
    review_path = args.review or args.products.with_name("review.json")
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(products, review, args.title, args.min_mentions), encoding="utf-8")
    print(f"written {args.output} ({len(products)} products)")


if __name__ == "__main__":
    main()
