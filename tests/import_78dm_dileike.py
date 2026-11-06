"""Complete 迪雷克 1/100 拼装系列 (斑鸠 / 翠鸟 / 孔雀) from 78dm.

Existing video-sourced 翠鸟 is completed in place; 斑鸠 and 孔雀 are new.
孔雀 currently has no 78dm price/date, so both stay NULL.
Default is a dry run; `--apply` writes.
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

MANIFEST = "outputs/78dm/dileike/products.json"
MAKER = "迪雷克"
LINE = "1/100"
EXISTING = {"翠鸟": "翠鸟"}


def parse_release_date(value: str) -> date | None:
    value = value or ""
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
    return f"{amounts[0]}元" if amounts else value


def build_detail(product: dict) -> str:
    lines = [
        ("78dm", product.get("url", "")),
        ("78dm名称", product.get("name", "")),
        ("版本", product.get("version", "")),
        ("发售时间", product.get("release_date", "")),
        ("比例", product.get("scale", "")),
        ("材料", product.get("material", "")),
        ("规格", product.get("specification", "")),
        ("玩具分类", product.get("toy_category", "")),
        ("来源分类", product.get("source_category", "")),
    ]
    return "\n".join(f"{key}: {value}" for key, value in lines if value)


def display_name(product: dict) -> str:
    name = product["name"].strip()
    return re.sub(r"^ZAW-S\d+\s+", "", name)


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
    if len(products) != 3:
        raise SystemExit(f"expected 3 products, got {len(products)}")

    with SessionLocal() as session:
        maker = session.scalar(select(Manufacturer).where(Manufacturer.name == MAKER))
        if maker is None:
            raise SystemExit(f"manufacturer missing: {MAKER}")
        line = session.scalar(
            select(ProductLine).where(
                ProductLine.manufacturer_id == maker.id,
                ProductLine.name == LINE,
            )
        )
        if line is None:
            line = ProductLine(manufacturer_id=maker.id, name=LINE)
            session.add(line)
            session.flush()
        rows = {row.kit_name: row for row in session.scalars(
            select(Product).where(Product.manufacturer_id == maker.id)
        )}

        updates = []
        inserts = []
        for product in products:
            name = display_name(product)
            row = rows.get(EXISTING.get(name, name))
            price = normalize_price(product.get("price", ""))
            release = parse_release_date(product.get("release_date", ""))
            detail = build_detail(product)
            aliases = [product["name"].strip(), name]
            if row is None:
                inserts.append((name, product, price, release, detail, aliases))
                continue
            changes = {}
            if row.product_code is None:
                changes["product_code"] = product["name"].split()[0]
            if row.work is None:
                changes["work"] = "原创"
            if row.edition is None:
                changes["edition"] = "普通版"
            if row.release_channel is None:
                changes["release_channel"] = "regular"
            if price and row.price != price:
                changes["price"] = price
            if row.release_date is None and release:
                changes["release_date"] = release
            if "78dm" not in (row.detail or ""):
                prefix = f"{row.detail.rstrip()}\n\n" if row.detail else ""
                changes["detail"] = prefix + detail
            merged = row.aliases
            for alias in aliases:
                merged = append_alias(merged, alias)
            if merged != (row.aliases or ""):
                changes["aliases"] = merged
            if changes:
                updates.append((row, name, changes))

        print(f"updates {len(updates)}; inserts {len(inserts)}")
        for row, name, changes in updates:
            print(f"  UPDATE {row.kit_name} -> {sorted(changes)}")
        for name, product, price, release, detail, aliases in inserts:
            print(f"  INSERT {name} | {product['name']} | {price} | {release}")

        if not args.apply:
            print("dry run; pass --apply to write")
            return

        for row, _, changes in updates:
            for field in ("product_code", "work", "edition", "release_channel", "price", "release_date", "detail", "aliases"):
                if field in changes:
                    setattr(row, field, changes[field])

        for name, product, price, release, detail, aliases in inserts:
            session.add(
                Product(
                    manufacturer_id=maker.id,
                    product_line_id=line.id,
                    kit_name=name,
                    product_code=product["name"].split()[0],
                    work="原创",
                    edition="普通版",
                    release_channel="regular",
                    price=price,
                    release_date=release,
                    detail=detail,
                    source=product["url"],
                    aliases=";".join(aliases),
                )
            )
        session.commit()
        print(f"updated {len(updates)}, inserted {len(inserts)}")


if __name__ == "__main__":
    main()
