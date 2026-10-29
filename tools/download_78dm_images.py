"""Download cover images for an existing 78dm products.json manifest.

Reads imports/78dm/<series>/products.json, downloads each image_url into
imports/78dm/<series>/images/<id>.<ext>, and updates image_file relative paths.
Existing files are skipped, so the downloader is resumable.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)


def existing(images_dir: Path, product_id: str) -> Path | None:
    for path in images_dir.glob(f"{product_id}.*"):
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def download(product: dict, images_dir: Path) -> tuple[str, str | None, str | None]:
    product_id = str(product["id"])
    found = existing(images_dir, product_id)
    if found:
        return product_id, str(found.relative_to(images_dir.parent)), None

    image_url = product.get("image_url") or ""
    if not image_url:
        return product_id, None, "no image_url"

    last: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=45,
                headers={
                    "User-Agent": UA,
                    "Referer": product.get("url", "https://acg.78dm.net/"),
                    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
                },
            ) as client:
                response = client.get(image_url)
            if response.status_code != 200 or not response.content:
                raise RuntimeError(f"HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
            if not content_type.startswith("image/"):
                raise RuntimeError(f"not an image: {content_type}")
            suffix = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".jpg"
            if suffix == ".jpe":
                suffix = ".jpg"
            destination = images_dir / f"{product_id}{suffix}"
            destination.write_bytes(response.content)
            return product_id, str(destination.relative_to(images_dir.parent)), None
        except Exception as exc:
            last = exc
            time.sleep(0.5 * (attempt + 1))
    return product_id, None, str(last)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="e.g. imports/78dm/341672")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    out_dir = (ROOT / args.dir).resolve()
    manifest_path = out_dir / "products.json"
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    products = manifest["products"]
    done = 0
    failed: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download, product, images_dir): product for product in products}
        for future in as_completed(futures):
            product = futures[future]
            product_id, relative, error = future.result()
            if relative:
                product["image_file"] = relative
                product.pop("image_error", None)
                done += 1
            else:
                product["image_file"] = ""
                product["image_error"] = error or "download failed"
                failed.append((product_id, error or "download failed"))
            print(f"[{done + len(failed)}/{len(products)}] {product_id}: {relative or error}")

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"downloaded/skipped {done}; failed {len(failed)}")
    if failed:
        for product_id, error in failed:
            print(f"  failed {product_id}: {error}")


if __name__ == "__main__":
    main()
