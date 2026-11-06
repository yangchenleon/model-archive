"""Import the five new manufacturers from the curated 78dm manifest.

Scope: 壹理创玩 / 创模玩 / 所罗门模玩 / 圣斯基 / 御模道, 拼装 products only.
The manifest in outputs/78dm/new-mfgs/products.json is already curated:
unreleased/卫星/成品 rows are removed, and line/work/channel/edition are mapped
per IP. Default is a dry run; `--apply` writes to PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
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

MANIFEST = "outputs/78dm/new-mfgs/products.json"
MAKERS = ("壹理创玩", "创模玩", "所罗门模玩", "圣斯基", "御模道")

# 78dm id -> existing DB product name (video-sourced rows)
EXISTING = {
    "447662": "魔神凯撒（彩透版）",
}


def parse_release_date(value: str) -> date | None:
    value = value or ""
    iso = re.match(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", value)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", value)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
    quarter = re.search(r"第?([一二三四1234])季度", value)
    year = re.search(r"(\d{4})\s*年", value)
    if quarter and year:
        month = {"一": 1, "二": 4, "三": 7, "四": 10}[quarter.group(1)]
        return date(int(year.group(1)), month, 1)
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
    if len(products) != 116:
        raise SystemExit(f"expected 116 curated products, got {len(products)}")

    prepared = []
    for product in products:
        line = (product.get("line") or "").strip()
        if not line:
            raise SystemExit(f"missing line: {product['id']} {product['name']}")
        prepared.append(
            {
                "id": product["id"],
                "name": product["name"].strip(),
                "manufacturer": product["manufacturer"],
                "line": line,
                "work": (product.get("work") or line).strip(),
                "edition": (product.get("edition") or "普通版").strip(),
                "channel": product.get("channel") or "regular",
                "price": normalize_price(product.get("price", "")),
                "release_date": parse_release_date(product.get("release_date", "")),
                "detail": build_detail(product),
                "source": product.get("url", ""),
            }
        )

    keys = Counter((item["manufacturer"], item["line"], item["name"]) for item in prepared)
    dupes = {key: count for key, count in keys.items() if count > 1}
    if dupes:
        raise SystemExit(f"duplicate product names in manifest: {dupes}")

    with SessionLocal() as session:
        makers = {}
        for maker_name in MAKERS:
            maker = session.scalar(select(Manufacturer).where(Manufacturer.name == maker_name))
            if maker is None:
                maker = Manufacturer(name=maker_name, category="guomo", tier=3)
                session.add(maker)
                session.flush()
            makers[maker_name] = maker

        products_by_maker = {}
        for maker_name, maker in makers.items():
            rows = list(session.scalars(select(Product).where(Product.manufacturer_id == maker.id)))
            products_by_maker[maker_name] = rows

        lines_by_maker = {}
        for maker_name, maker in makers.items():
            lines = list(session.scalars(select(ProductLine).where(ProductLine.manufacturer_id == maker.id)))
            lines_by_maker[maker_name] = {line.name: line for line in lines}

        updates = []
        inserts = []
        for item in prepared:
            maker_rows = products_by_maker[item["manufacturer"]]
            if item["id"] == "439169" and sum(
                1 for row in maker_rows if row.kit_name.startswith("EVA 超可动拼装盲盒 ")
            ) == 7:
                # The 端盒 row was split by tests/split_eva_blindbox.py; don't
                # let the parent manifest row overwrite one of the variants.
                continue
            by_name = {row.kit_name: row for row in maker_rows}
            by_source = {row.source: row for row in maker_rows if row.source}
            row = by_name.get(EXISTING.get(item["id"], "")) or by_source.get(item["source"])
            if row is None:
                inserts.append(item)
                continue

            changes = {}
            if row.product_line_id is None:
                changes["line"] = item["line"]
            if row.work is None:
                changes["work"] = item["work"]
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
            alias = append_alias(row.aliases, item["name"])
            if alias != (row.aliases or ""):
                changes["aliases"] = alias
            if changes:
                updates.append((row, item, changes))

        print(f"manifest: {len(prepared)} products")
        print(f"existing updates: {len(updates)}")
        for row, item, changes in updates:
            print(f"  [{row.kit_name}] -> {item['manufacturer']}/{item['line']} fields={sorted(changes)}")
        print(f"new products: {len(inserts)}")
        for (maker, line), count in sorted(Counter((i["manufacturer"], i["line"]) for i in inserts).items()):
            print(f"  {maker}/{line}: {count}")

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for row, item, changes in updates:
            if "line" in changes:
                line = lines_by_maker[item["manufacturer"]].get(item["line"])
                if line is None:
                    line = ProductLine(manufacturer_id=row.manufacturer_id, name=item["line"])
                    session.add(line)
                    session.flush()
                    lines_by_maker[item["manufacturer"]][line.name] = line
                row.product_line_id = line.id
            for field in ("work", "edition", "release_channel", "price", "release_date", "detail", "aliases"):
                if field in changes:
                    setattr(row, field, changes[field])

        for item in inserts:
            maker = makers[item["manufacturer"]]
            line = lines_by_maker[item["manufacturer"]].get(item["line"])
            if line is None:
                line = ProductLine(manufacturer_id=maker.id, name=item["line"])
                session.add(line)
                session.flush()
                lines_by_maker[item["manufacturer"]][line.name] = line
            session.add(
                Product(
                    manufacturer_id=maker.id,
                    product_line_id=line.id,
                    kit_name=item["name"],
                    work=item["work"],
                    edition=item["edition"],
                    release_channel=item["channel"],
                    price=item["price"],
                    release_date=item["release_date"],
                    detail=item["detail"],
                    source=item["source"],
                    aliases=item["name"],
                )
            )

        session.commit()
        print(f"updated {len(updates)}, inserted {len(inserts)}")


if __name__ == "__main__":
    main()
