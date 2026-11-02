"""Update 无限新星 (INERA无限系) products from the scraped 78dm 395396 manifest.

Scope agreed with the user:
- only existing DB rows are updated; names and lines stay untouched;
- price and release date take 78dm non-empty values, 简介 is appended to detail;
- 利扎德（红色涂装限量版） has no 78dm page and stays as it is;
- 先驱 keeps the staged price 159-189元 instead of 78dm's 154.

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
from app.models import Manufacturer, Product  # noqa: E402

MANUFACTURER = "无限新星"
INTRO_MARKER = "78dm简介："

# 78dm page id -> current DB kit_name; overrides replace the page value.
UPDATES: list[tuple[str, str, dict]] = [
    ("404310", "雷霆 THUNDER BOLT", {}),
    ("415971", "雷霆·魔鬼鱼 MOBULIDAE", {}),
    ("416661", "利扎德 LIZARD", {}),
    ("438907", "芬里尔 FENRIR", {}),
    ("439163", "雷霆·魔鬼鱼（极速版）", {}),
    ("444530", "雷霆（苍雷配色）", {}),
    ("444871", "利扎德（极地鲨）", {}),
    ("445618", "青鸢 AZURE FALCON", {}),
    ("409564", "曙光 AURORA", {}),
    ("395399", "裁决 RUlING", {}),
    ("412053", "裁决（小芒限定配色）", {}),
    ("395398", "先驱 TRAILBLAZER", {"price": "159-189元"}),
]

PRICE_PREFIX_RE = re.compile(r"^(零售版|定价|售价|官方定价|建议零售价)\s*")


def normalize_price(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    value = PRICE_PREFIX_RE.sub("", value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(人民币|元|日元|RMB|JPY)?", value)
    if not match:
        return value
    amount, unit = match.group(1), match.group(2) or ""
    if unit in {"日元", "JPY"}:
        return f"{amount}日元"
    return f"{amount}元"


def parse_release_date(value: str) -> date | None:
    value = value or ""
    iso = re.match(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", value)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    quarter = re.search(r"第([一二三四1234])季度|([Qq])([1-4])", value)
    year_match = re.search(r"(\d{4})\s*年", value)
    if quarter and year_match:
        token = quarter.group(1) or quarter.group(3)
        month = {"一": 1, "二": 4, "三": 7, "四": 10, "1": 1, "2": 4, "3": 7, "4": 10}[token]
        return date(int(year_match.group(1)), month, 1)
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", value)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
        except ValueError:
            return None
    if year_match:
        return date(int(year_match.group(1)), 1, 1)
    return None


def append_intro(detail: str | None, intro: str) -> str | None:
    intro = (intro or "").strip()
    if not intro:
        return detail
    if detail and INTRO_MARKER in detail:
        return detail
    block = f"{INTRO_MARKER}\n{intro}"
    if detail:
        return f"{detail.rstrip()}\n\n{block}"
    return block


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="imports/78dm/395396/products.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    pages = {product["id"]: product for product in data["products"]}

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == MANUFACTURER))
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {MANUFACTURER}")
        products = list(
            session.scalars(select(Product).where(Product.manufacturer_id == manufacturer.id))
        )
        by_name = {row.kit_name: row for row in products}

        changes: list[tuple[Product, dict]] = []
        problems: list[str] = []
        for page_id, kit_name, overrides in UPDATES:
            page = pages.get(page_id)
            if page is None:
                problems.append(f"78dm page {page_id} missing from manifest")
                continue
            row = by_name.get(kit_name)
            if row is None:
                problems.append(f"DB product not found: {kit_name}")
                continue

            updates: dict = {}
            price = overrides.get("price") or normalize_price(page.get("price", ""))
            if price and price != (row.price or ""):
                updates["price"] = (row.price, price)
            release_text = overrides.get("date") or page.get("release_date", "")
            release = parse_release_date(release_text) if release_text else None
            if release and release != row.release_date:
                updates["release_date"] = (row.release_date, release)
            detail = append_intro(row.detail, page.get("intro", ""))
            if detail != row.detail:
                updates["detail"] = (row.detail, detail)
            if updates:
                changes.append((row, updates))

        if problems:
            print("PROBLEMS:")
            for problem in problems:
                print("  -", problem)
            raise SystemExit(f"{len(problems)} problems, nothing written")

        print(f"rows with changes: {len(changes)}")
        for row, updates in changes:
            print(f"\n[{row.kit_name}]")
            for field, (before, after) in updates.items():
                if field == "detail":
                    print("  detail: +78dm简介")
                else:
                    print(f"  {field}: {before!r} -> {after!r}")

        untouched = [row.kit_name for row in products if row.kit_name not in {name for _, name, _ in UPDATES}]
        print(f"\nnot matched (left untouched): {untouched}")

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for row, updates in changes:
            for field, (_, after) in updates.items():
                setattr(row, field, after)
        session.commit()

    print(f"updated {len(changes)}")


if __name__ == "__main__":
    main()
