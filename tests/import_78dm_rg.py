"""Import the scraped 78dm RG manifest into the local PostgreSQL database.

Default is a dry run. Use --apply to replace the current 万代 / RG products.

The import keeps all 235 products on the existing RG line. IP/work is filled
only for the explicitly non-Gundam subcategories (EVANGELION, 勇者王, 机动警察);
Gundam work is left NULL until it can be sourced reliably.

Run from the repository root:
    .venv/bin/python tests/import_78dm_rg.py --apply
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
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://model_archive:model_archive_dev@localhost:15432/model_archive",
)

from sqlalchemy import delete, select, update  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Manufacturer, Product, ProductLine, ReviewItem  # noqa: E402

WORK_BY_CATEGORY = {
    "EVANGELION系列": "EVANGELION",
    "勇者王系列": "勇者王",
    "机动警察系列": "机动警察",
}

# 78dm's table leaves the code empty for a few normal-version pages even though
# the card/page sequence has a number. Keep only explicit, reviewed overrides.
CODE_OVERRIDES = {
    "446468": "44",  # 陆战型高达: the last of the 44 normal-version entries
}


def clean_name(value: str) -> str:
    return re.sub(r"^\s*\d+\s+", "", value or "").strip()


def normalize_code(value: str | None) -> str | None:
    if not value:
        return None
    if re.fullmatch(r"RG\d+", value, flags=re.I):
        return value[2:]
    return value


def code_for(product: dict) -> str | None:
    code = normalize_code(product.get("code"))
    if code:
        return code
    prefix = re.match(r"^\s*(\d+)\s+", product.get("name", ""))
    if prefix:
        return prefix.group(1).zfill(2)
    return CODE_OVERRIDES.get(str(product.get("id")))


def parse_release_date(value: str) -> date | None:
    match = re.search(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?", value or "")
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        day = int(match.group(3) or 1)
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(r"(\d{4})年", value or "")
    if match:
        try:
            return date(int(match.group(1)), 1, 1)
        except ValueError:
            return None
    return None


def build_detail(product: dict, image_file: str) -> str:
    lines = [
        ("78dm", product.get("url", "")),
        ("78dm名称", product.get("name", "")),
        ("版本", product.get("version", "")),
        ("发售时间", product.get("release_date", "")),
        ("比例", product.get("scale", "")),
        ("人物名", product.get("character", "")),
        ("材料", product.get("material", "")),
        ("规格", product.get("specification", "")),
        ("玩具分类", product.get("toy_category", "")),
        ("来源分类", product.get("source_category", "")),
        ("封面", f"imports/78dm/341672/{image_file}" if image_file else ""),
    ]
    return "\n".join(f"{key}: {value}" for key, value in lines if value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="imports/78dm/341672/products.json")
    parser.add_argument("--manufacturer", default="万代")
    parser.add_argument("--line", default="RG")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    manifest_path = ROOT / args.manifest
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    products = data["products"]
    if len(products) != 235:
        raise SystemExit(f"expected 235 products, got {len(products)}")

    prepared: list[dict] = []
    names: set[str] = set()
    for product in products:
        kit_name = clean_name(product.get("name", ""))
        if not kit_name:
            raise SystemExit(f"empty name for {product.get('id')}")
        if kit_name in names:
            raise SystemExit(f"duplicate kit_name after cleaning: {kit_name}")
        names.add(kit_name)
        prepared.append({
            "id": uuid4(),
            "manufacturer_id": None,
            "product_line_id": None,
            "product_code": code_for(product),
            "kit_name": kit_name,
            "work": WORK_BY_CATEGORY.get(product.get("source_category", "")),
            "release_channel": product.get("channel"),
            "release_date": parse_release_date(product.get("release_date", "")),
            "detail": build_detail(product, product.get("image_file", "")),
            "source": product.get("url", ""),
            "price": product.get("price") or None,
        })

    print("products", len(prepared))
    print("works", Counter(item["work"] for item in prepared))
    print("channels", Counter(item["release_channel"] for item in prepared))
    print("first", prepared[0]["kit_name"], prepared[0]["product_code"], prepared[0]["release_channel"])
    print("last", prepared[-1]["kit_name"], prepared[-1]["product_code"], prepared[-1]["release_channel"])
    if not args.apply:
        print("dry run; pass --apply to replace the existing RG products")
        return

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == args.manufacturer))
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {args.manufacturer}")
        line = session.scalar(
            select(ProductLine).where(
                ProductLine.manufacturer_id == manufacturer.id,
                ProductLine.name == args.line,
            )
        )
        if line is None:
            raise SystemExit(f"line not found: {args.manufacturer} / {args.line}")

        old_ids = list(session.scalars(
            select(Product.id).where(
                Product.manufacturer_id == manufacturer.id,
                Product.product_line_id == line.id,
            )
        ))
        print(f"replacing {len(old_ids)} existing {args.manufacturer}/{args.line} products")

        if old_ids:
            session.execute(
                update(ReviewItem)
                .where(ReviewItem.product_id.in_(old_ids))
                .values(
                    state="pending",
                    product_id=None,
                    manufacturer_id=None,
                    product_line_id=None,
                    skip_reason=None,
                    reviewed_at=None,
                )
            )
            # Same reset semantics as the regular product delete endpoint.
            session.execute(delete(Product).where(Product.id.in_(old_ids)))

        for item in prepared:
            item["manufacturer_id"] = manufacturer.id
            item["product_line_id"] = line.id
        session.execute(Product.__table__.insert(), prepared)
        session.commit()

    print(f"inserted {len(prepared)} products; replaced {len(old_ids)}")


if __name__ == "__main__":
    main()
