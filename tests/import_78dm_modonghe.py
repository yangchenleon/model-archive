"""Import the scraped 78dm 摩动核 (383484) manifest into PostgreSQL.

Default is a dry run. `--apply` updates matched 摩动核 products and inserts the
可动Q版 干将 product.

Scope agreed with the user:
- `仅CG图参考化商品（暂）` is skipped entirely.
- `可动Q版系列` only adds 干将 (MNPQ-XH04); the other seven are ignored.
- Every other 78dm product only updates an existing DB row; nothing is deleted
  and no other product is created.
- Only non-empty 78dm values override: price, release date, product code (when
  missing or known-wrong) and the 简介 appended to `detail`. Names, lines,
  channels, editions, crafts, work and source stay untouched.
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

MANUFACTURER = "摩动核"
EXCLUDED_SECTIONS = {"仅CG图参考化商品（暂）"}
Q_SECTION = "星甲魂将传 可动Q版系列"
Q_KEEP_CODES = {"MNPQ-XH04"}
NEW_LINE = "可动Q版系列"
NEW_KIT_NAME = "干将"

# 78dm's 编号 column is sometimes wrong (敖丙 精制版 lists MNP-XH03). The code in
# the product name is authoritative, so these rows are corrected explicitly.
CODE_FIXES = {"386211": "MNP-XH03E"}

# Rows where two DB products share a code or the names differ, so matching by
# code/name alone is ambiguous.
MATCH_OVERRIDES = {
    "446466": "白起 精制版（通贩）",
    "445442": "赵云·玉兰白龙驹 威武色",
}

INTRO_MARKER = "78dm简介："

CODE_RE = re.compile(r"^\s*(MNPQ?-[A-Z]{2}\d+[A-Z]{0,3}|BV-[A-Z]{2}\d+[A-Z]{0,3})\s*[|｜]?\s*", re.I)
PRICE_PREFIX_RE = re.compile(r"^(零售版|定价|售价|官方定价|建议零售价)\s*")


def strip_code(name: str) -> str:
    return CODE_RE.sub("", name or "").strip()


def code_from_name(name: str) -> str:
    match = CODE_RE.match(name or "")
    return normalize_code(match.group(1)) if match else ""


def normalize_code(value: str) -> str:
    return re.sub(r"[\s|｜]+", "", value or "").upper()


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
    if unit in {"人民币", "元", "RMB"}:
        return f"{amount}元"
    return f"{amount}元"


def parse_release_date(value: str) -> date | None:
    value = value or ""
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
    parser.add_argument("--manifest", default="outputs/78dm/383484/products.json")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    source_products = [
        product
        for product in data["products"]
        if product.get("source_category") not in EXCLUDED_SECTIONS
    ]
    kept: list[dict] = []
    for product in source_products:
        code = code_from_name(product.get("name", "")) or normalize_code(product.get("code", ""))
        if product.get("source_category") == Q_SECTION and code not in Q_KEEP_CODES:
            continue
        kept.append({**product, "_code": code})

    with SessionLocal() as session:
        manufacturer = session.scalar(
            select(Manufacturer).where(Manufacturer.name == MANUFACTURER)
        )
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {MANUFACTURER}")
        rows = list(
            session.scalars(select(Product).where(Product.manufacturer_id == manufacturer.id))
        )
        by_name: dict[str, list[Product]] = {}
        by_code: dict[str, list[Product]] = {}
        for row in rows:
            by_name.setdefault(row.kit_name, []).append(row)
            if row.product_code:
                by_code.setdefault(normalize_code(row.product_code), []).append(row)

        planned: list[tuple[dict, Product | dict]] = []
        problems: list[str] = []
        for product in kept:
            code = product["_code"]
            base_name = strip_code(product.get("name", ""))
            if product.get("source_category") == Q_SECTION and code in Q_KEEP_CODES:
                existing = by_code.get(code)
                if existing:
                    planned.append((product, existing[0]))
                else:
                    planned.append((product, {"new": True, "base_name": base_name}))
                continue

            target: Product | None = None
            override = MATCH_OVERRIDES.get(product["id"])
            if override:
                candidates = by_name.get(override, [])
                if len(candidates) != 1:
                    problems.append(f'{product["id"]} {product["name"]}: override {override} matched {len(candidates)}')
                    continue
                target = candidates[0]
            else:
                candidates = by_code.get(code, [])
                if len(candidates) == 1:
                    target = candidates[0]
                elif len(candidates) > 1:
                    narrowed = [row for row in candidates if row.kit_name == base_name]
                    if len(narrowed) == 1:
                        target = narrowed[0]
                    else:
                        problems.append(
                            f'{product["id"]} {product["name"]}: code {code} matches {[r.kit_name for r in candidates]}'
                        )
                        continue
                else:
                    named = by_name.get(base_name, [])
                    if len(named) == 1:
                        target = named[0]
                    else:
                        problems.append(f'{product["id"]} {product["name"]}: no DB match (code={code})')
                        continue
            planned.append((product, target))

        if problems:
            print("UNMATCHED / AMBIGUOUS:")
            for problem in problems:
                print("  -", problem)
            raise SystemExit(f"{len(problems)} products could not be matched")

        changes: list[tuple[Product | dict, dict]] = []
        for product, target in planned:
            if isinstance(target, dict):
                continue
            updates: dict = {}
            price = normalize_price(product.get("price", ""))
            if price and price != (target.price or ""):
                updates["price"] = (target.price, price)
            release = parse_release_date(product.get("release_date", ""))
            if release and release != target.release_date:
                updates["release_date"] = (target.release_date, release)
            name_code = code_from_name(product.get("name", "")) or normalize_code(product.get("code", ""))
            if name_code:
                current = normalize_code(target.product_code or "")
                if not current:
                    updates["product_code"] = (target.product_code, name_code)
                elif product["id"] in CODE_FIXES and current != CODE_FIXES[product["id"]]:
                    updates["product_code"] = (target.product_code, CODE_FIXES[product["id"]])
            detail = append_intro(target.detail, product.get("intro", ""))
            if detail != target.detail:
                updates["detail"] = (target.detail, detail)
            if updates:
                changes.append((target, updates))

        new_rows = [
            (product, target)
            for product, target in planned
            if isinstance(target, dict)
        ]

        print(f"78dm products kept: {len(kept)} (skipped {len(data['products']) - len(kept)})")
        print(f"matched existing: {len(planned) - len(new_rows)}, to insert: {len(new_rows)}")
        print(f"rows with changes: {len(changes)}")

        for target, updates in changes:
            print(f"\n[{target.kit_name}]")
            for field, (before, after) in updates.items():
                if field == "detail":
                    print("  detail: +78dm简介")
                else:
                    print(f"  {field}: {before!r} -> {after!r}")

        for product, target in new_rows:
            print(f"\n[new] {NEW_KIT_NAME}")
            print(f"  code={product['_code']} line={NEW_LINE} "
                  f"price={normalize_price(product.get('price', ''))!r} "
                  f"date={parse_release_date(product.get('release_date', ''))}")
            print(f"  intro={'yes' if product.get('intro') else 'no'}")

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for target, updates in changes:
            for field, (_, after) in updates.items():
                setattr(target, field, after)

        for product, target in new_rows:
            line = session.scalar(
                select(ProductLine).where(
                    ProductLine.manufacturer_id == manufacturer.id,
                    ProductLine.name == NEW_LINE,
                )
            )
            if line is None:
                line = ProductLine(manufacturer_id=manufacturer.id, name=NEW_LINE)
                session.add(line)
                session.flush()
            session.add(
                Product(
                    manufacturer_id=manufacturer.id,
                    product_line_id=line.id,
                    product_code=product["_code"],
                    kit_name=NEW_KIT_NAME,
                    work=None,
                    release_channel="regular",
                    edition="普通版",
                    release_date=parse_release_date(product.get("release_date", "")),
                    detail=append_intro(None, product.get("intro", "")),
                    source=product.get("url", ""),
                    price=normalize_price(product.get("price", "")) or None,
                )
            )
        session.commit()

    print(f"updated {len(changes)} products, inserted {len(new_rows)}")


if __name__ == "__main__":
    main()
