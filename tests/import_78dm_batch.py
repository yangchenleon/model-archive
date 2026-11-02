"""Batch upsert for five 78dm series (2026-11).

User rules:
- existing rows only get metadata (price/release date/简介); name, line, work and
  the rest stay untouched;
- missing products are added, using 78dm names with the code prefix stripped;
- new rows take line/work from the 78dm section: a meaningful series name is used
  as both line and work, otherwise `原创拼装`; 橘猫's QOSMOS sections use
  line=QOSMOS and work=铁甲小宝/火影忍者;
- 橘猫 only imports the QOSMOS sections.

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

INTRO_MARKER = "78dm简介："
FALLBACK_LINE = "原创拼装"

# section name -> (line, work); sections not listed are skipped for that series.
SERIES = [
    {
        "manifest": "imports/78dm/420592/products.json",
        "manufacturer": "驭意堂",
        "sections": {"玄机铸型录系列": ("玄机铸型录系列", "玄机铸型录系列")},
        "existing": [
            ("420599", "皓灵白帝", {}),
        ],
    },
    {
        "manifest": "imports/78dm/416211/products.json",
        "manufacturer": "机核工业",
        "sections": {"塑料拼装系列": (FALLBACK_LINE, FALLBACK_LINE)},
        "existing": [
            ("416216", "卡戎 CHARON（JH-001）", {}),
            ("416220", "天卫·奥伯龙 OBERON", {}),
            ("424908", "地卫·希切尔 IXCHEL", {}),
            ("442204", "奥伯龙 异色版（机核工业×小芒联名）", {}),
            ("443591", "奥伯龙·改", {}),
        ],
    },
    {
        "manifest": "imports/78dm/407068/products.json",
        "manufacturer": "铭匠传",
        "sections": {"铭匠传拼装系列  普通版": (FALLBACK_LINE, FALLBACK_LINE)},
        "existing": [
            ("409131", "赤鬼若·清盛（初代）", {}),
            ("416290", "天狗判官·义经", {}),
            ("425049", "逍遥子 XIAOYAOZI（×SUNDAY HOBBY）", {}),
            ("430593", "雪之章·雪鬼（赤鬼若限定换色版）", {}),
            ("439153", "蓝鲸系列·猞猁 LYNX（REA-03）", {}),
            ("439154", "始皇帝·嬴政", {}),
        ],
    },
    {
        "manifest": "imports/78dm/443611/products.json",
        "manufacturer": "光冕",
        "sections": {"普通款": (FALLBACK_LINE, FALLBACK_LINE)},
        "existing": [
            ("446410", "斗士一型·亚撒", {}),
        ],
    },
    {
        "manifest": "imports/78dm/351234/products.json",
        "manufacturer": "橘猫工业",
        "sections": {
            "QOSMOS 铁甲小宝系列": ("QOSMOS", "铁甲小宝"),
            "QOSMOS 火影忍者系列": ("QOSMOS", "火影忍者"),
        },
        "existing": [],
    },
]

CODE_PREFIX_RE = re.compile(r"^\s*([A-Za-z]{2,6}[-_ ]?\d{1,4}[A-Za-z]?)\s+")
PRICE_PREFIX_RE = re.compile(r"^(零售版|定价|售价|官方定价|建议零售价)\s*")
PRICE_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def split_code(name: str) -> tuple[str, str]:
    match = CODE_PREFIX_RE.match(name or "")
    if not match:
        return name, ""
    return name[match.end():].strip(), match.group(1).replace(" ", "")


def normalize_price(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    value = PRICE_PREFIX_RE.sub("", value)
    amounts = PRICE_NUMBER_RE.findall(value)
    if not amounts:
        return value
    if "日元" in value or "JPY" in value:
        return f"{amounts[0]}日元"
    if len(amounts) > 1 and "/" in value:
        return f"{'/'.join(amounts[:2])}元"
    return f"{amounts[0]}元"


def parse_release_date(value: str) -> date | None:
    value = value or ""
    iso = re.match(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$", value)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    # An explicit month/day is more precise than a quarter in the same string
    # (e.g. "预计二季度发售2024年08月" should be August).
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", value)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
        except ValueError:
            return None
    quarter = re.search(r"第?([一二三四1234])季度|([Qq])([1-4])", value)
    year_match = re.search(r"(\d{4})\s*年", value)
    if quarter and year_match:
        token = quarter.group(1) or quarter.group(3)
        month = {"一": 1, "二": 4, "三": 7, "四": 10, "1": 1, "2": 4, "3": 7, "4": 10}[token]
        return date(int(year_match.group(1)), month, 1)
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


def channel_and_edition(version: str) -> tuple[str, str | None]:
    version = (version or "").strip()
    if "WF" in version or "会场" in version:
        return "event", version or None
    if "限定" in version or "抽奖" in version:
        return "limited", version or None
    return "regular", version or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    all_changes: list[tuple[object, str, dict]] = []
    all_new: list[dict] = []
    all_problems: list[str] = []

    with SessionLocal() as session:
        for spec in SERIES:
            data = json.loads((ROOT / spec["manifest"]).read_text(encoding="utf-8"))
            pages = {product["id"]: product for product in data["products"]}
            manufacturer = session.scalar(
                select(Manufacturer).where(Manufacturer.name == spec["manufacturer"])
            )
            if manufacturer is None:
                if not args.apply:
                    print(f"[{spec['manufacturer']}] 厂商不存在，--apply 时会新建")
                    manufacturer_lines: list[str] = []
                    existing_products: list[Product] = []
                else:
                    manufacturer = Manufacturer(name=spec["manufacturer"], category="guomo", tier=3)
                    session.add(manufacturer)
                    session.flush()
                    manufacturer_lines = []
                    existing_products = []
            else:
                existing_products = list(
                    session.scalars(select(Product).where(Product.manufacturer_id == manufacturer.id))
                )
            by_name = {row.kit_name: row for row in existing_products}

            used_pages: set[str] = set()
            for page_id, kit_name, overrides in spec["existing"]:
                page = pages.get(page_id)
                if page is None:
                    all_problems.append(f"{spec['manufacturer']}: 78dm page {page_id} missing")
                    continue
                row = by_name.get(kit_name)
                if row is None:
                    all_problems.append(f"{spec['manufacturer']}: DB product not found: {kit_name}")
                    continue
                used_pages.add(page_id)

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
                    all_changes.append((row.id, row.kit_name, updates))

            existing_line_names = {
                row.product_line_ref.name for row in existing_products if row.product_line_ref
            }
            for page_id, page in pages.items():
                if page_id in used_pages:
                    continue
                section = (page.get("source_category") or "").strip()
                rule = spec["sections"].get(section)
                if rule is None:
                    # fall back to whitespace-insensitive match
                    for key, value in spec["sections"].items():
                        if " ".join(key.split()) == " ".join(section.split()):
                            rule = value
                            break
                if rule is None:
                    continue
                line_name, work = rule
                name, name_code = split_code(page.get("name", ""))
                if any(row.kit_name == name for row in existing_products):
                    continue
                code = name_code or (page.get("code") or "").strip()
                channel, edition = channel_and_edition(page.get("version", ""))
                all_new.append(
                    {
                        "manufacturer": spec["manufacturer"],
                        "line": line_name,
                        "work": work,
                        "kit_name": name,
                        "product_code": code or None,
                        "price": normalize_price(page.get("price", "")) or None,
                        "release_date": parse_release_date(page.get("release_date", "")),
                        "release_channel": channel,
                        "edition": edition,
                        "detail": append_intro(None, page.get("intro", ""))
                        or f"78dm：{page.get('url', '')}",
                        "source": page.get("url", ""),
                    }
                )

    if all_problems:
        print("PROBLEMS:")
        for problem in all_problems:
            print("  -", problem)
        raise SystemExit(f"{len(all_problems)} problems, nothing written")

    print(f"existing updates: {len(all_changes)}")
    for _, kit_name, updates in all_changes:
        print(f"\n[{kit_name}]")
        for field, (before, after) in updates.items():
            if field == "detail":
                print("  detail: +78dm简介")
            else:
                print(f"  {field}: {before!r} -> {after!r}")

    print(f"\nnew products: {len(all_new)}")
    for item in all_new:
        print(
            f"  [{item['manufacturer']}/{item['line']}] {item['kit_name']} "
            f"code={item['product_code']} work={item['work']} price={item['price']} "
            f"date={item['release_date']} channel={item['release_channel']}"
        )

    if not args.apply:
        print("\ndry run; pass --apply to write")
        return

    with SessionLocal() as session:
        for product_id, _, updates in all_changes:
            row = session.get(Product, product_id)
            for field, (_, after) in updates.items():
                setattr(row, field, after)
        for item in all_new:
            manufacturer = session.scalar(
                select(Manufacturer).where(Manufacturer.name == item["manufacturer"])
            )
            if manufacturer is None:
                manufacturer = Manufacturer(name=item["manufacturer"], category="guomo", tier=3)
                session.add(manufacturer)
                session.flush()
            line = session.scalar(
                select(ProductLine).where(
                    ProductLine.manufacturer_id == manufacturer.id,
                    ProductLine.name == item["line"],
                )
            )
            if line is None:
                line = ProductLine(manufacturer_id=manufacturer.id, name=item["line"])
                session.add(line)
                session.flush()
            session.add(
                Product(
                    manufacturer_id=manufacturer.id,
                    product_line_id=line.id,
                    product_code=item["product_code"],
                    kit_name=item["kit_name"],
                    work=item["work"],
                    release_channel=item["release_channel"],
                    edition=item["edition"],
                    release_date=item["release_date"],
                    detail=item["detail"],
                    source=item["source"],
                    price=item["price"],
                )
            )
        session.commit()

    print(f"updated {len(all_changes)}, inserted {len(all_new)}")


if __name__ == "__main__":
    main()
