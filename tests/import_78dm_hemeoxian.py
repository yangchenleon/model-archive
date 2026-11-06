"""Update 和模线 products from the scraped 78dm 420002 manifest.

Scope agreed with the user:
- only existing DB rows are updated; names/lines stay as they are, except
  兰德·科茜基妮 -> 铁锈蔷薇【兰德·科茜基妮】;
- price and release date take 78dm non-empty values (per-variant prices where
  78dm merges 普通版/典藏版), and 简介 is appended to `detail`;
- Red Hood（红莲） is a duplicate of 小红帽 and gets deleted;
- 赤血·百合 is the only new product.

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

from sqlalchemy import func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Asset, CollectionItem, Manufacturer, Product, ProductLine, ReviewItem  # noqa: E402

MANUFACTURER = "和模线"
LINE = "机娘"
INTRO_MARKER = "78dm简介："
DELETE_NAME = "Red Hood（红莲）"

# 78dm page id, current DB kit_name, per-row overrides.
# price/date override the page value; intro=False skips the 简介 append;
# rename_to renames the row after finding it by kit_name.
UPDATES: list[tuple[str, str, dict]] = [
    ("414670", "塔斯提尔 套装版", {}),
    ("414670", "塔斯提尔 单体版", {"price": "99元", "date": "2024-01-01", "intro": False}),
    ("416401", "塔斯提尔 Red Death 小芒节目限定版", {}),
    ("422947", "塔斯提尔 会场限定版-ver.I.C.E", {}),
    ("416400", "孤影 套装版", {}),
    ("416400", "孤影 单体版", {"price": "99元", "intro": False}),
    ("435267", "孤影 会场限定版-噩梦幻影", {}),
    ("429106", "拳击手 巴奇（BAKI）", {}),
    ("445288", "拳击手 巴奇·极限爆发", {}),
    ("429109", "蝙蝠侠：阿卡姆骑士", {}),
    ("439542", "超限零点 衣物配件包", {"price": "79元"}),
    ("426788", "星花·百合-MK3", {}),
    ("443422", "兰德·科茜基妮", {"price": "199→218元", "rename_to": "铁锈蔷薇【兰德·科茜基妮】"}),
    ("420971", "玖莲", {"price": "188→218元"}),
    ("420004", "小红帽", {}),
    ("418998", "岳山·应龙号（通贩版）", {"price": "188元", "intro": False}),
    ("418998", "岳山·应龙号（典藏版）", {"price": "288元", "intro": False}),
    ("447139", "岳山·应龙号（焰绡霞）", {}),
    ("447140", "岳山·应龙号（魅紫）", {}),
    ("390122", "雷神", {}),
    ("422948", "雷神 会场限定版-奥尔劳格之力", {}),
    ("423282", "雷神-苍雷形态 X11联名定制版", {}),
    ("423631", "猫狗特攻队-可洛基", {}),
    ("423630", "猫狗特攻队-哈二奇", {}),
    ("418400", "牛机-巴弗力翁", {}),
]

NEW_PRODUCT = {"page": "444514", "kit_name": "赤血·百合"}

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
    parser.add_argument("--manifest", default="outputs/78dm/420002/products.json")
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
            row = by_name.get(kit_name) or by_name.get(overrides.get("rename_to", ""))
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
            if overrides.get("intro", True):
                detail = append_intro(row.detail, page.get("intro", ""))
                if detail != row.detail:
                    updates["detail"] = (row.detail, detail)
            new_name = overrides.get("rename_to")
            if new_name and row.kit_name != new_name:
                updates["kit_name"] = (row.kit_name, new_name)
            if updates:
                changes.append((row, updates))

        target = by_name.get(DELETE_NAME)
        if target is not None:
            refs = {
                "assets": session.scalar(select(func.count()).select_from(Asset).where(Asset.product_id == target.id)),
                "collections": session.scalar(
                    select(func.count()).select_from(CollectionItem).where(CollectionItem.product_id == target.id)
                ),
                "reviews": session.scalar(
                    select(func.count()).select_from(ReviewItem).where(ReviewItem.product_id == target.id)
                ),
            }
            if any(refs.values()):
                problems.append(f"refusing to delete {DELETE_NAME}: references {refs}")

        new_page = pages.get(NEW_PRODUCT["page"])
        if new_page is None:
            problems.append("78dm page for 赤血·百合 missing")
        existing_new = by_name.get(NEW_PRODUCT["kit_name"])
        if existing_new is not None and existing_new.id != (target.id if target else None):
            new_page = None
            print(f"{NEW_PRODUCT['kit_name']} already exists; skipping insert")

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

        print("\ndelete:", DELETE_NAME if target is not None else "(already absent)")
        if new_page is not None:
            print(
                "insert: 赤血·百合 | price=", normalize_price(new_page.get("price", "")),
                "| date=", parse_release_date(new_page.get("release_date", "")),
                "| intro=", "yes" if new_page.get("intro") else "no",
            )

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for row, updates in changes:
            for field, (_, after) in updates.items():
                setattr(row, field, after)
        if target is not None:
            session.delete(target)
        if new_page is not None:
            line = session.scalar(
                select(ProductLine).where(
                    ProductLine.manufacturer_id == manufacturer.id,
                    ProductLine.name == LINE,
                )
            )
            if line is None:
                line = ProductLine(manufacturer_id=manufacturer.id, name=LINE)
                session.add(line)
                session.flush()
            session.add(
                Product(
                    manufacturer_id=manufacturer.id,
                    product_line_id=line.id,
                    product_code=None,
                    kit_name=NEW_PRODUCT["kit_name"],
                    work=None,
                    release_channel="event",
                    edition=new_page.get("version", "") or None,
                    release_date=parse_release_date(new_page.get("release_date", "")),
                    detail=append_intro(None, new_page.get("intro", "")),
                    source=new_page.get("url", ""),
                    price=normalize_price(new_page.get("price", "")) or None,
                )
            )
        session.commit()

    print(f"updated {len(changes)}, deleted {1 if target else 0}, inserted {1 if new_page else 0}")


if __name__ == "__main__":
    main()
