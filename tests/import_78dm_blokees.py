"""Import 布鲁可 传奇版 products from the targeted 78dm crawl.

Scope: the four 78dm 布鲁可 series pages supplied by the user, filtered to the
传奇版 family: 传奇版, 传奇版Lite, 传奇金选, 传奇版EP拓展包, plus the two
限量产品 entries whose names contain 传奇版.

Default is a dry run; `--apply` writes to PostgreSQL. Existing video-sourced
rows are matched explicitly and only get missing metadata filled in, so their
display names and notes are preserved.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://model_archive:model_archive_dev@localhost:15432/model_archive",
)

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Manufacturer, Product, ProductLine  # noqa: E402

MANIFEST = "outputs/78dm/blokees-legendary/products.json"
IMAGE_ROOT = "outputs/78dm/blokees-legendary"

# 78dm page id -> existing DB product name (视频来源的老条目)
EXISTING = {
    "446081": "奥特之王",
    "446443": "新世纪福音战士TV版二号机",
    "446944": "甲斗",
}

IP_BY_SERIES = {
    "布鲁可变形金刚系列": "变形金刚",
    "布鲁可奥特曼系列": "奥特曼",
    "布鲁可日系IP授权系列": None,  # per-product: 新世纪福音战士 / 火影忍者
    "布鲁可假面骑士系列": "假面骑士",
}
IP_BY_SECTION = {
    "新世纪福音战士（传奇版）": "新世纪福音战士",
    "火影忍者（传奇版）": "火影忍者",
}

NAME_PREFIXES = ("传奇版 ", "传奇金选 ")


def clean_name(name: str) -> str:
    cleaned = (name or "").strip()
    for prefix in NAME_PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    # 限量产品: "必胜客联名款 传奇版 闪耀迪迦" -> "必胜客联名款 闪耀迪迦"
    return cleaned.replace("传奇版 ", "").strip()


def line_for(product: dict) -> str:
    series = product.get("series", "")
    ip = IP_BY_SERIES.get(series)
    if ip:
        return ip
    section = product.get("source_category", "")
    if section in IP_BY_SECTION:
        return IP_BY_SECTION[section]
    raise SystemExit(f"cannot decide line for {product.get('id')} {series} / {section}")


def edition_for(product: dict) -> str:
    section = product.get("source_category", "")
    if section.startswith("传奇版Lite"):
        return "传奇版Lite"
    if section.startswith("传奇版EP拓展包"):
        return "传奇版配件包"
    if "传奇金选" in section:
        return "传奇金选"
    return "传奇版"


def channel_for(product: dict) -> str:
    version = product.get("version", "") or ""
    if "限定" in version or "抽选" in version:
        return "limited"
    return "regular"


def parse_release_date(value: str) -> date | None:
    value = value or ""
    iso = re.match(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", value)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", value)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
    year = re.search(r"(\d{4})\s*年", value)
    if year:
        return date(int(year.group(1)), 1, 1)
    return None


def normalize_price(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    amounts = re.findall(r"(\d+(?:\.\d+)?)", value)
    if not amounts:
        return value
    suffix = "日元" if "日元" in value else "元"
    return f"{amounts[0]}{suffix}"


def build_detail(product: dict) -> str:
    image_file = product.get("image_file", "")
    lines = [
        ("78dm", product.get("url", "")),
        ("78dm名称", product.get("name", "")),
        ("版本", product.get("version", "")),
        ("发售时间", product.get("release_date", "")),
        ("人物名", product.get("character", "")),
        ("材料", product.get("material", "")),
        ("规格", product.get("specification", "")),
        ("玩具分类", product.get("toy_category", "")),
        ("来源分类", product.get("source_category", "")),
        ("封面", f"{IMAGE_ROOT}/{image_file}" if image_file else ""),
    ]
    text = "\n".join(f"{key}: {value}" for key, value in lines if value)
    intro = (product.get("intro") or "").strip()
    if intro:
        text += f"\n\n78dm简介：\n{intro}"
    return text


def append_alias(existing: str | None, value: str) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    if value not in parts:
        parts.append(value)
    return ";".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    products = data["products"]
    if len(products) != 45:
        raise SystemExit(f"expected 45 products, got {len(products)}")

    prepared = []
    for product in products:
        name = clean_name(product.get("name", ""))
        if not name:
            raise SystemExit(f"empty name: {product.get('id')}")
        prepared.append(
            {
                "id": product["id"],
                "name": name,
                "source_name": product.get("name", ""),
                "line": line_for(product),
                "edition": edition_for(product),
                "channel": channel_for(product),
                "price": normalize_price(product.get("price", "")),
                "release_date": parse_release_date(product.get("release_date", "")),
                "detail": build_detail(product),
                "source": product.get("url", ""),
            }
        )

    names = [item["name"] for item in prepared if item["id"] not in EXISTING]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate display names after normalization")

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == "布鲁可"))
        if manufacturer is None:
            raise SystemExit("manufacturer 布鲁可 not found")
        existing_products = list(
            session.scalars(select(Product).where(Product.manufacturer_id == manufacturer.id))
        )
        by_name = {row.kit_name: row for row in existing_products}
        by_source = {row.source: row for row in existing_products if row.source}
        lines = list(
            session.scalars(select(ProductLine).where(ProductLine.manufacturer_id == manufacturer.id))
        )
        by_line = {row.name: row for row in lines}

        updates = []
        inserts = []
        for item in prepared:
            row = by_name.get(EXISTING.get(item["id"], "")) or by_source.get(item["source"])
            if row is None:
                inserts.append(item)
                continue

            changes = {}
            if row.product_line_id is None:
                changes["line"] = item["line"]
            if row.work is None:
                changes["work"] = item["line"]
            if row.edition is None:
                changes["edition"] = item["edition"]
            if row.release_channel is None:
                changes["release_channel"] = item["channel"]
            if not row.price and item["price"]:
                changes["price"] = item["price"]
            if row.release_date is None and item["release_date"]:
                changes["release_date"] = item["release_date"]
            if item["source"] and "78dm" not in (row.detail or ""):
                prefix = f"{row.detail.rstrip()}\n\n" if row.detail else ""
                changes["detail"] = prefix + item["detail"]
            alias = append_alias(row.aliases, item["source_name"])
            if alias != (row.aliases or ""):
                changes["aliases"] = alias
            if changes:
                updates.append((row, item, changes))

        print(f"manifest: {len(products)} products")
        print(f"existing updates: {len(updates)}")
        for row, item, changes in updates:
            print(f"  [{row.kit_name}] -> line={item['line']} fields={sorted(changes)}")
        print(f"new products: {len(inserts)}")
        for item in inserts:
            print(
                f"  [{item['line']}] {item['name']} | {item['edition']} | {item['channel']} | "
                f"{item['price']} | {item['release_date']}"
            )

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for row, item, changes in updates:
            if "line" in changes:
                line = by_line.get(item["line"])
                if line is None:
                    line = ProductLine(manufacturer_id=manufacturer.id, name=item["line"])
                    session.add(line)
                    session.flush()
                    by_line[line.name] = line
                row.product_line_id = line.id
            for field in ("work", "edition", "release_channel", "price", "release_date", "detail", "aliases"):
                if field in changes:
                    setattr(row, field, changes[field])

        for item in inserts:
            line = by_line.get(item["line"])
            if line is None:
                line = ProductLine(manufacturer_id=manufacturer.id, name=item["line"])
                session.add(line)
                session.flush()
                by_line[line.name] = line
            session.add(
                Product(
                    manufacturer_id=manufacturer.id,
                    product_line_id=line.id,
                    kit_name=item["name"],
                    work=item["line"],
                    edition=item["edition"],
                    release_channel=item["channel"],
                    price=item["price"],
                    release_date=item["release_date"],
                    detail=item["detail"],
                    source=item["source"],
                    aliases=item["source_name"],
                )
            )

        session.commit()
        print(f"updated {len(updates)}, inserted {len(inserts)}")


if __name__ == "__main__":
    main()
