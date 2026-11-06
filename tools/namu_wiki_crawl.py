# -*- coding: utf-8 -*-
"""Crawl a namu.wiki list page into a local markdown knowledge base.

Direct access is blocked by Cloudflare, so every request goes through the
Google Translate proxy (en-namu-wiki.translate.goog). The machine's DNS is
poisoned for these hosts, so IPs are resolved over DoH (Cloudflare) and the
socket connects to the IP directly with SNI.

Output layout (default outputs/knowledge/namu-rg):
    index.md            generated table of contents with local links
    pages/<slug>.md     one converted article per wiki page
    manifest.json       wiki path -> {slug, title, source}

Run:  .venv/bin/python tools/namu_wiki_crawl.py --limit 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import html2text
from bs4 import BeautifulSoup

PROXY = "en-namu-wiki.translate.goog"
WIKI = "https://namu.wiki"
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".tmp" / "namu-cache"
QUERY = "?_x_tr_sl=auto&_x_tr_tl=zh-CN&_x_tr_hl=zh-CN&_x_tr_pto=wapp"


_DOH: dict[str, str] = {}


def doh(host: str) -> str:
    if host in _DOH:
        return _DOH[host]
    url = f"https://cloudflare-dns.com/dns-query?name={host}&type=A"
    req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    ips = [a["data"] for a in data.get("Answer", []) if a["type"] == 1]
    _DOH[host] = ips[0] if ips else ""
    return _DOH[host]


def http_get(path: str, host: str = PROXY) -> tuple[int, str]:
    ip = doh(host)
    if not ip:
        raise RuntimeError(f"no A record for {host}")
    ctx = ssl.create_default_context()
    with socket.create_connection((ip, 443), timeout=40) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            request = (
                f"GET {path}{QUERY} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36\r\n"
                "Accept: text/html,application/xhtml+xml\r\n"
                "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8\r\n"
                "Connection: close\r\n\r\n"
            )
            ssock.sendall(request.encode())
            chunks = []
            while True:
                data = ssock.recv(65536)
                if not data:
                    break
                chunks.append(data)
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.decode("iso-8859-1", "ignore").splitlines()[0] if head else ""
    status = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
    if b"chunked" in head.lower():
        out, rest = [], body
        while rest:
            line, _, rest = rest.partition(b"\r\n")
            size = int(line.split(b";")[0], 16)
            if size == 0:
                break
            out.append(rest[:size])
            rest = rest[size + 2:]
        body = b"".join(out)
    return status, body.decode("utf-8", "ignore")


def fetch_bytes(url: str) -> tuple[int, str, bytes]:
    """Fetch a binary asset directly (i.namu.wiki allows it with a referer)."""
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    path = parts.path + (f"?{parts.query}" if parts.query else "")
    ip = doh(host)
    if not ip:
        return 0, "", b""
    ctx = ssl.create_default_context()
    with socket.create_connection((ip, 443), timeout=40) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            request = (
                f"GET {path} HTTP/1.1\r\nHost: {host}\r\n"
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36\r\n"
                "Accept: image/avif,image/webp,image/*,*/*\r\n"
                "Referer: https://namu.wiki/\r\n"
                "Connection: close\r\n\r\n"
            )
            ssock.sendall(request.encode())
            chunks = []
            while True:
                data = ssock.recv(65536)
                if not data:
                    break
                chunks.append(data)
    raw = b"".join(chunks)
    head, _, body = raw.partition(b"\r\n\r\n")
    header_text = head.decode("iso-8859-1", "ignore")
    lines = header_text.splitlines()
    status = int(lines[0].split()[1]) if lines and len(lines[0].split()) > 1 else 0
    ctype = ""
    for line in lines[1:]:
        if line.lower().startswith("content-type:"):
            ctype = line.split(":", 1)[1].strip().split(";")[0]
    if "chunked" in header_text.lower():
        out, rest = [], body
        while rest:
            line, _, rest = rest.partition(b"\r\n")
            try:
                size = int(line.split(b";")[0], 16)
            except ValueError:
                break
            if size == 0:
                break
            out.append(rest[:size])
            rest = rest[size + 2:]
        body = b"".join(out)
    return status, ctype, body


EXT_BY_TYPE = {
    "image/webp": ".webp",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/avif": ".avif",
}


class ImageStore:
    def __init__(self, assets: Path, enabled: bool = True):
        self.enabled = enabled
        self.assets = assets
        self.cache = CACHE / "img"
        self.assets.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.seen: dict[str, str | None] = {}

    def local(self, src: str) -> str | None:
        if not self.enabled or not src or src.startswith("data:"):
            return None
        url = "https:" + src if src.startswith("//") else src
        if not url.startswith("http"):
            return None
        key = hashlib.sha1(url.encode()).hexdigest()[:16]
        if key in self.seen:
            return self.seen[key]
        cached = next(self.cache.glob(f"{key}.*"), None)
        if cached is not None:
            data = cached.read_bytes()
            ext = cached.suffix
        else:
            try:
                status, ctype, data = fetch_bytes(url)
            except Exception:  # noqa: BLE001 - a broken image must not kill the crawl
                status, ctype, data = 0, "", b""
            if status != 200 or len(data) < 200:
                self.seen[key] = None
                return None
            ext = EXT_BY_TYPE.get(ctype, Path(urllib.parse.urlsplit(url).path).suffix or ".bin")
            cached = self.cache / f"{key}{ext}"
            cached.write_bytes(data)
            time.sleep(0.15)
        name = f"{key}{ext}"
        target = self.assets / name
        if not target.exists():
            target.write_bytes(data)
        self.seen[key] = name
        return name


def cached_get(path: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(path.encode()).hexdigest()
    f = CACHE / f"{key}.html"
    if f.exists() and f.stat().st_size > 2000:
        return f.read_text(encoding="utf-8")
    for attempt in range(3):
        status, html = http_get(path)
        if status == 200 and len(html) > 2000:
            f.write_text(html, encoding="utf-8")
            return html
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"fetch failed for {path}")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:80]


def article_of(html: str) -> tuple[str, BeautifulSoup | None]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True).replace(" - NamuWiki", "") if soup.title else ""
    art = soup.find("article")
    if art is None:
        return title, None
    body = max(art.find_all("div", recursive=False), key=lambda d: len(d.get_text()), default=None)
    return title, body


def build_md(body: BeautifulSoup, title: str, source: str, resolver, rel: str, current: str,
             images: ImageStore | None = None, asset_rel: str = "../assets/") -> str:
    if images is not None:
        for img in body.find_all("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src.lower().split("?")[0].endswith(".svg"):
                img.decompose()
                continue
            try:
                filesize = int(img.get("data-filesize") or 0)
            except ValueError:
                filesize = 0
            if filesize and filesize < 4000:
                img.decompose()
                continue
            name = images.local(src)
            if name:
                img["src"] = asset_rel + name
            else:
                img.decompose()
    for a in body.find_all("a", href=True):
        skip_prefixes = ("분류:", "파일:", "틀:", "특수:")
        href = a["href"]
        if "/w/" not in href:
            continue
        raw = href.split("/w/", 1)[1].split("?")[0]
        raw = raw.split("#")[0]
        target = urllib.parse.unquote(raw)
        if not target or target.startswith(skip_prefixes):
            a.unwrap() if hasattr(a, "unwrap") else None
            continue
        if target == current:
            a.replace_with(a.get_text(" ", strip=True))
            continue
        text = a.get_text(" ", strip=True) or a.get("title", "")
        a["href"] = rel + resolver(target, text) + ".md"
    for tag in body.find_all(["script", "style"]):
        tag.decompose()
    conv = html2text.HTML2Text()
    conv.body_width = 0
    conv.ignore_links = False
    conv.ignore_images = False
    md = conv.handle(str(body))
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    front = f"---\ntitle: {json.dumps(title, ensure_ascii=False)}\nsource: {source}\nfetched: {date.today().isoformat()}\n---\n\n"
    return front + f"# {title}\n\n" + md + "\n"


class Resolver:
    def __init__(self, manifest: dict, outdir: Path):
        self.manifest = manifest
        self.outdir = outdir
        self.taken = {v["slug"] for v in manifest.values()}

    def slug(self, path: str, text: str = "") -> str:
        entry = self.manifest.get(path)
        if entry:
            return entry["slug"]
        base = slugify(text)
        if not base:
            base = f"p-{hashlib.sha1(path.encode()).hexdigest()[:8]}"
        slug = base
        n = 2
        while slug in self.taken:
            slug = f"{base}-{n}"
            n += 1
        self.taken.add(slug)
        self.manifest[path] = {"slug": slug, "title": text}
        return slug

    def __call__(self, path: str, text: str) -> str:
        return self.slug(path, text)


def parse_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find("article")
    body = max(art.find_all("div", recursive=False), key=lambda d: len(d.get_text()))
    rows = []
    for table in body.find_all("table"):
        all_rows = table.find_all("tr")
        header_index = None
        for i, tr in enumerate(all_rows):
            if "product name" in tr.get_text(" ", strip=True).lower():
                header_index = i
                break
        if header_index is None:
            continue
        heading = ""
        prev = table.find_previous(["h2", "h3", "h4"])
        if prev:
            heading = prev.get_text(" ", strip=True)
        for tr in all_rows[header_index + 1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]
            if texts and texts[0] in ("order", "product name", "1/60 scale"):
                continue
            link = tr.find("a", href=True)
            path = None
            link_text = ""
            if link and "/w/" in link["href"]:
                path = urllib.parse.unquote(link["href"].split("/w/", 1)[1].split("?")[0])
                link_text = link.get_text(" ", strip=True)
            rows.append({"section": heading, "cells": texts, "path": path, "link_text": link_text})
    return rows


def write_index(rows: list[dict], resolver: Resolver, outdir: Path, list_path: str) -> None:
    lines = [
        "# namu.wiki · Real Grade 列表（本地快照）",
        "",
        f"- 来源：{WIKI}{list_path}",
        "- 抓取方式：Google 翻译代理（直连被 Cloudflare 拦截）",
        "- 名称是机器翻译的英文，仅供检索与对账，不作为展示名依据",
        "",
        f"共 {len(rows)} 条。",
        "",
    ]
    section = None
    for row in rows:
        if row["section"] != section:
            section = row["section"]
            title = section.split(".")[-1].strip() or "未分组"
            lines += ["", f"## {title}", "", "| 商品 | 机号 | 发售 | 价格 | 作品 |", "|---|---|---|---|---|"]
        cells = row["cells"]
        # 通贩表有「序号」列，其余表格没有，按第一格是不是数字判断
        offset = 1 if cells and re.fullmatch(r"\d+", cells[0]) else 0
        name = cells[offset] if len(cells) > offset else ""
        model = cells[offset + 1] if len(cells) > offset + 1 else ""
        date_ = cells[offset + 2] if len(cells) > offset + 2 else ""
        price = cells[offset + 3] if len(cells) > offset + 3 else ""
        work = cells[offset + 4] if len(cells) > offset + 4 else ""
        entry = resolver.manifest.get(row["path"]) if row["path"] else None
        exists = entry and (outdir / "pages" / f"{entry['slug']}.md").exists()
        label = f"[{name}](pages/{entry['slug']}.md)" if exists else name
        lines.append(f"| {label} | {model} | {date_} | {price} | {work} |")
    (outdir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/knowledge/namu-rg")
    ap.add_argument("--list-path", default="/w/리얼 그레이드/리스트")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--delay", type=float, default=0.8)
    ap.add_argument("--follow", type=int, default=0, help="crawl N linked pages that are still missing")
    ap.add_argument("--no-images", action="store_true", help="skip downloading images")
    ap.add_argument("--skip-existing", action="store_true", help="skip pages whose md already exists")
    args = ap.parse_args()

    outdir = ROOT / args.out
    (outdir / "pages").mkdir(parents=True, exist_ok=True)
    images = ImageStore(outdir / "assets", enabled=not args.no_images)
    manifest_file = outdir / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {}

    list_path = "/w/" + urllib.parse.quote(args.list_path.replace("/w/", ""))
    html = cached_get(list_path)
    rows = parse_list(html)
    print(f"list rows: {len(rows)}")

    resolver = Resolver(manifest, outdir)
    resolver.slug(args.list_path.replace("/w/", ""), "rg-list")

    crawled = 0
    for row in rows:
        if not row["path"]:
            continue
        if args.limit and crawled >= args.limit:
            break
        path = "/w/" + urllib.parse.quote(row["path"])
        try:
            page = cached_get(path)
        except Exception as exc:  # noqa: BLE001
            print("skip", row["path"], exc)
            continue
        title, body = article_of(page)
        if body is None:
            continue
        slug = resolver.slug(row["path"], (row["link_text"] or title))
        target = outdir / "pages" / f"{slug}.md"
        if args.skip_existing and target.exists() and "![" in target.read_text(encoding="utf-8"):
            continue
        md = build_md(body, title, WIKI + path, resolver, "../pages/", row["path"], images)
        target.write_text(md, encoding="utf-8")
        crawled += 1
        print(f"[{crawled}] {slug}  ({len(md)} chars)")
        time.sleep(args.delay)

    title, body = article_of(html)
    if body is not None:
        md = build_md(body, title or "Real Grade/List", WIKI + list_path, resolver, "../pages/", args.list_path.replace("/w/", ""), images)
        (outdir / "pages" / "rg-list.md").write_text(md, encoding="utf-8")

    if args.follow:
        pending = [
            p for p, meta in manifest.items()
            if not (outdir / "pages" / f"{meta['slug']}.md").exists()
        ]
        print(f"follow queue: {len(pending)}, crawling {min(len(pending), args.follow)}")
        done = 0
        for target in pending[: args.follow]:
            path = "/w/" + urllib.parse.quote(target)
            try:
                page = cached_get(path)
            except Exception as exc:  # noqa: BLE001
                print("skip", target, exc)
                continue
            page_title, page_body = article_of(page)
            if page_body is None:
                continue
            slug = resolver.slug(target, page_title)
            md = build_md(page_body, page_title, WIKI + path, resolver, "../pages/", target, images)
            (outdir / "pages" / f"{slug}.md").write_text(md, encoding="utf-8")
            done += 1
            if done % 20 == 0:
                print(f"  followed {done}")
            time.sleep(args.delay)
        print("followed:", done)

    write_index(rows, resolver, outdir, list_path)
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("manifest entries:", len(manifest))


if __name__ == "__main__":
    main()
