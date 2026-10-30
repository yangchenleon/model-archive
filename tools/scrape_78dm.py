"""Scrape a 78dm series page into a local JSON manifest and cover images.

Usage:
    .venv/bin/python tools/scrape_78dm.py \
        --url https://acg.78dm.net/ct/341672.html \
        --out imports/78dm/341672

The site requires a valid `_identity` cookie. By default it reads `78cookie2`
from the repository root; the cookie is never written to the output.

This tool deliberately does not import rows into PostgreSQL. It only builds a
local, reviewable dataset under imports/ (gitignored).
"""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://acg.78dm.net"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)
def infer_channel(section_name: str, version: str) -> str | None:
    if section_name == "普通版":
        return "regular"
    if section_name == "网络限定版":
        return "pb"
    if section_name == "其他限定版":
        return "limited"
    if section_name == "参考出品/开发中商品":
        if "限定" in version:
            return "limited"
        return None
    if "网络限定" in version or "网限" in version or version.upper() == "PB":
        return "pb"
    if "限定" in version:
        return "limited"
    if "普通版" in version:
        return "regular"
    return None


def clean(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\xa0", " ").strip()


def load_cookie(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    return raw.split(";", 1)[0].strip()


def make_client(cookie: str) -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=60,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": f"{BASE}/",
            "Cookie": cookie,
        },
    )


def get(client: httpx.Client, url: str, *, retries: int = 3) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.get(url)
            if response.status_code == 200:
                return response
            last = RuntimeError(f"HTTP {response.status_code}: {url}")
        except Exception as exc:  # network errors are retried
            last = exc
        time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(str(last))


def parse_series(html_text: str) -> dict:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    title = clean(title_match.group(1)) if title_match else ""

    short_name = ""
    manufacturer = ""
    description = ""
    for match in re.finditer(
        r'<td class="table-header">(.*?)</td>\s*<td[^>]*>(.*?)</td>',
        html_text,
        re.S,
    ):
        key = clean(match.group(1))
        value = clean(match.group(2))
        if key == "简称":
            short_name = value
        elif key == "厂商":
            manufacturer = value

    intro = re.search(
        r'<div id="introduction"[^>]*>.*?<p[^>]*>(.*?)</p>',
        html_text,
        re.S,
    )
    if intro:
        description = clean(intro.group(1))

    starts = [m.start() for m in re.finditer(r'<div class="item normal-list">', html_text)]
    end_marker = html_text.find("<!-- 系列单品列表 end -->")
    sections = []
    seen_ids: set[str] = set()
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else (end_marker if end_marker > start else len(html_text))
        chunk = html_text[start:end]
        name_match = re.search(
            r'<p class="is-flex"><span class="line"></span><span>(.*?)</span><span>共(\d+)款</span></p>',
            chunk,
            re.S,
        )
        sub_name = clean(name_match.group(1)) if name_match else ""
        sub_count = int(name_match.group(2)) if name_match else 0
        sub_link = re.search(r'href="/ct/(\d+)\.html"[^>]*>级别分类详情', chunk)
        cards = []
        for card in re.finditer(r'<a href="/ct/(\d+)\.html"[^>]*>(.*?)</a>', chunk, re.S):
            ct_id = card.group(1)
            body = card.group(2)
            if ct_id in seen_ids:
                continue
            seen_ids.add(ct_id)
            name = re.search(r'title="([^"]*)"', body)
            if not name:
                name = re.search(r"<p>(.*?)</p>", body, re.S)
            image = re.search(r'data-src="([^"]+)"', body) or re.search(r'src="([^"]+)"', body)
            cards.append(
                {
                    "id": ct_id,
                    "url": f"{BASE}/ct/{ct_id}.html",
                    "card_name": clean(name.group(1)) if name else "",
                    "card_image": image.group(1) if image else "",
                }
            )
        sections.append(
            {
                "name": sub_name,
                "count": sub_count,
                "url": f"{BASE}/ct/{sub_link.group(1)}.html" if sub_link else "",
                "products": cards,
            }
        )

    return {
        "title": title,
        "short_name": short_name,
        "manufacturer": manufacturer,
        "description": description,
        "sections": sections,
        "product_count": len(seen_ids),
    }


def parse_product(html_text: str, url: str, ct_id: str, section: dict, series: dict) -> dict:
    fields: dict[str, str] = {}
    for match in re.finditer(
        r'<td class="table-header">(.*?)</td>\s*<td[^>]*>(.*?)</td>',
        html_text,
        re.S,
    ):
        key = clean(match.group(1))
        value = clean(match.group(2))
        if key:
            fields[key] = value

    images = re.findall(
        r'<img[^>]+src="([^"]*bbs-attachment-cdn\.78dm\.net/upload/[^"]+)"',
        html_text,
        re.I,
    )
    image_url = ""
    cover = re.search(r"onclick=\"showImage\(this,\s*'([^']+)'\)\s*;?\s*\"", html_text)
    if cover:
        image_url = cover.group(1)
    if not image_url:
        for candidate in images:
            if "w1200h1200" in candidate:
                image_url = candidate
                break
    if not image_url and images:
        image_url = images[0]
    if image_url.startswith("//"):
        image_url = f"https:{image_url}"
    elif image_url.startswith("/"):
        image_url = urljoin(BASE, image_url)

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.I | re.S)
    page_title = clean(title_match.group(1)) if title_match else ""
    name = fields.get("名称") or page_title
    version = fields.get("版本", "")
    channel = infer_channel(section.get("name", ""), version)

    return {
        "id": ct_id,
        "url": url,
        "name": name,
        "page_title": page_title,
        "version": version,
        "code": fields.get("编号", ""),
        "price": fields.get("价格", ""),
        "release_date": fields.get("发售时间", ""),
        "scale": fields.get("比例", ""),
        "character": fields.get("人物名", ""),
        "manufacturer": fields.get("厂商", "") or series.get("manufacturer", ""),
        "series": fields.get("系列", "") or series.get("title", ""),
        "source_category": section.get("name", ""),
        "line": "RG",
        "channel": channel,
        "material": fields.get("材料种类", ""),
        "specification": fields.get("规格", ""),
        "toy_category": fields.get("玩具分类", ""),
        "image_url": image_url,
        "image_file": "",
        "fields": fields,
    }


def download_image(
    client: httpx.Client,
    image_url: str,
    destination: Path,
    referer: str,
    *,
    retries: int = 3,
) -> str:
    if not image_url:
        return ""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.get(
                image_url,
                headers={"Referer": referer, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
            )
            if response.status_code == 200 and response.content:
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
                if not content_type.startswith("image/"):
                    raise RuntimeError(f"not an image: {content_type}")
                suffix = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".jpg"
                if suffix == ".jpe":
                    suffix = ".jpg"
                destination = destination.with_suffix(suffix)
                destination.write_bytes(response.content)
                return str(destination)
            last = RuntimeError(f"HTTP {response.status_code}: {image_url}")
        except Exception as exc:
            last = exc
        time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(str(last))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=f"{BASE}/ct/341672.html")
    parser.add_argument("--out", required=True)
    parser.add_argument("--cookie", default=str(ROOT / "78cookie2"))
    parser.add_argument("--limit", type=int, default=0, help="only fetch the first N products")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--delay", type=float, default=0.25, help="seconds between product pages")
    args = parser.parse_args()

    out_dir = (ROOT / args.out).resolve()
    images_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    cookie = load_cookie(Path(args.cookie))
    client = make_client(cookie)
    series_html = get(client, args.url).text
    series = parse_series(series_html)
    series["source_url"] = args.url
    series["fetched_at"] = datetime.now(timezone.utc).isoformat()

    products: list[dict] = []
    seen: set[str] = set()
    for section in series["sections"]:
        if section.get("url"):
            try:
                section_html = get(client, section["url"]).text
                section_parsed = parse_series(section_html)
                section_parts = section_parsed.get("sections", [])
                if section_parts:
                    complete = next(
                        (part for part in section_parts if part.get("name") == section.get("name")),
                        section_parts[0],
                    )
                    section = {**section, "products": complete.get("products", section["products"])}
            except Exception as exc:
                print(f"[section error] {section.get('name')}: {exc}")
        for card in section["products"]:
            if args.limit and len(products) >= args.limit:
                break
            if card["id"] in seen:
                continue
            seen.add(card["id"])
            try:
                product_html = get(client, card["url"]).text
                product = parse_product(product_html, card["url"], card["id"], section, series)
                if not product["image_url"]:
                    product["image_url"] = card.get("card_image", "")
                if product["image_url"].startswith("//"):
                    product["image_url"] = f"https:{product['image_url']}"
                if not args.skip_images and product["image_url"]:
                    try:
                        product["image_file"] = download_image(
                            client,
                            product["image_url"],
                            images_dir / card["id"],
                            card["url"],
                        )
                    except Exception as exc:
                        product["image_error"] = str(exc)
                products.append(product)
                print(f"[{len(products)}] {product['name']} ({card['id']})")
            except Exception as exc:
                products.append({"id": card["id"], "url": card["url"], "error": str(exc)})
                print(f"[error] {card['id']}: {exc}")
            time.sleep(args.delay)
        if args.limit and len(products) >= args.limit:
            break

    series["products"] = products
    series["fetched_products"] = len(products)
    (out_dir / "series.json").write_text(
        json.dumps(series, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "products.json").write_text(
        json.dumps(
            {
                "source_url": args.url,
                "fetched_at": series["fetched_at"],
                "products": products,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out_dir / 'products.json'} ({len(products)} products)")
    client.close()


if __name__ == "__main__":
    main()
