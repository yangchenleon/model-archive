"""Import 万象聚变 TMS 系列 and GM-GODOMO kits from the curated 78dm crawl.

万象聚变 products are all re-grouped under line/work `TMS系列`; 天启 is the first
TMS kit. Three event variants missing from 78dm are added from the user's list:
WF2025 彩透, 2024 磨砂透明, 2025 机械透明.

GM-GODOMO is merged into the existing DB manufacturer `GM模型` (same 月渎/日曜
line), not duplicated. Default is a dry run; `--apply` writes.
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

MANIFEST = "outputs/78dm/tms/products.json"
MAKER_MAP = {"GM-GODOMO": "GM模型"}
LINE_BY_MAKER = {"万象聚变": "TMS系列", "GM模型": "拼装机甲"}
EXISTING_NAMES = {"流星": "流星", "月渎 全息影像版": "月渎（全息幻影）"}

MANUAL = [
    {
        "id": "manual-tianqi-wf2025-clear",
        "name": "天启 彩透版（WF2025）",
        "version": "WF2025限定",
        "price": "336人民币",
        "release_date": "2025年10月02日",
        "source": "https://m.blog.naver.com/kamiwind/224257629695",
        "channel": "event",
        "edition": "彩透版",
        "detail": "WF2025 上海会场限定，限定 200 体；现场价 336 元。参考：https://m.blog.naver.com/kamiwind/224257629695",
    },
]

# 2024/2025 的彩透与磨砂/机械透明是同一款，名称保留一个，另一个进 aliases。
EXTRA_ALIASES = {
    "天启 彩透版": ["天启 磨砂透明版"],
    "天启 彩透版（WF2025）": ["天启 机械透明版"],
}
DETAIL_NOTES = {
    "天启 彩透版": "同款说明：2024 彩透版与 2024 磨砂透明版为同一款。",
    "天启 彩透版（WF2025）": "同款说明：2025 彩透版与 2025 机械透明版为同一款。",
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


def edition_for(product: dict, channel: str) -> str:
    name = product.get("name", "")
    section = product.get("source_category", "")
    version = (product.get("version") or "").strip()
    if section == "配件包" or "配件包" in name:
        return "配件包"
    if "黑金" in name:
        return "黑金版"
    if "彩透" in name:
        return "彩透版"
    if "磨砂透明" in name:
        return "磨砂透明版"
    if "机械透明" in name:
        return "机械透明版"
    if "异色" in name:
        return "异色版"
    if "全息" in name:
        return "全息影像版"
    if channel == "regular":
        return "普通版"
    return version if version and version != "普通版" else "限定版"


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
    raw_products = data["products"]
    if len(raw_products) != 11:
        raise SystemExit(f"expected 11 crawled products, got {len(raw_products)}")

    prepared = []
    for product in raw_products:
        maker = MAKER_MAP.get(product["manufacturer"], product["manufacturer"])
        line = LINE_BY_MAKER[maker]
        text = " ".join([product["source_category"], product["version"], product["name"]])
        if any(key in text for key in ("WF", "ChinaJoy", "会场", "展")):
            channel = "event"
        elif "限定" in text or "限量" in text:
            channel = "limited"
        else:
            channel = "regular"
        prepared.append(
            {
                "id": product["id"],
                "name": product["name"].strip(),
                "manufacturer": maker,
                "line": line,
                "work": line,
                "edition": edition_for(product, channel),
                "channel": channel,
                "price": normalize_price(product.get("price", "")),
                "release_date": parse_release_date(product.get("release_date", "")),
                "detail": build_detail(product) + (
                    "\n\n" + DETAIL_NOTES[product["name"].strip()]
                    if product["name"].strip() in DETAIL_NOTES else ""
                ),
                "source": product.get("url", ""),
                "alias": product["name"].strip(),
                "extra_aliases": EXTRA_ALIASES.get(product["name"].strip(), []),
            }
        )

    for item in MANUAL:
        prepared.append(
            {
                "id": item["id"],
                "name": item["name"],
                "manufacturer": "万象聚变",
                "line": "TMS系列",
                "work": "TMS系列",
                "edition": item["edition"],
                "channel": item["channel"],
                "price": normalize_price(item["price"]),
                "release_date": parse_release_date(item["release_date"]),
                "detail": item["detail"] + (
                    "\n\n" + DETAIL_NOTES[item["name"]]
                    if item["name"] in DETAIL_NOTES else ""
                ),
                "source": item["source"],
                "alias": item["name"],
                "extra_aliases": EXTRA_ALIASES.get(item["name"], []),
            }
        )

    if len(prepared) != 12:
        raise SystemExit(f"expected 12 curated rows, got {len(prepared)}")

    keys = Counter((item["manufacturer"], item["line"], item["name"]) for item in prepared)
    dupes = {key: count for key, count in keys.items() if count > 1}
    if dupes:
        raise SystemExit(f"duplicate names: {dupes}")

    with SessionLocal() as session:
        makers = {}
        for maker_name in ("万象聚变", "GM模型"):
            maker = session.scalar(select(Manufacturer).where(Manufacturer.name == maker_name))
            if maker is None:
                maker = Manufacturer(name=maker_name, category="guomo", tier=3)
                session.add(maker)
                session.flush()
            makers[maker_name] = maker

        rows_by_maker = {}
        for maker_name, maker in makers.items():
            rows_by_maker[maker_name] = list(
                session.scalars(select(Product).where(Product.manufacturer_id == maker.id))
            )

        updates = []
        inserts = []
        for item in prepared:
            rows = rows_by_maker[item["manufacturer"]]
            by_name = {row.kit_name: row for row in rows}
            by_source = {row.source: row for row in rows if row.source}
            row = by_name.get(EXISTING_NAMES.get(item["name"], item["name"])) or by_source.get(item["source"])
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
            if item["source"] and "78dm" not in (row.detail or "") and row.source != item["source"]:
                prefix = f"{row.detail.rstrip()}\n\n" if row.detail else ""
                changes["detail"] = prefix + item["detail"]
            alias = row.aliases
            for alias_value in [item["alias"], *item["extra_aliases"]]:
                alias = append_alias(alias, alias_value)
            if alias != (row.aliases or ""):
                changes["aliases"] = alias
            if changes:
                updates.append((row, item, changes))

        print(f"prepared {len(prepared)}; updates {len(updates)}; inserts {len(inserts)}")
        for row, item, changes in updates:
            print(f"  UPDATE {item['manufacturer']}/{item['line']} {row.kit_name} -> {sorted(changes)}")
        for item in inserts:
            print(f"  INSERT {item['manufacturer']}/{item['line']} {item['name']} | {item['edition']} | {item['channel']} | {item['price']} | {item['release_date']}")

        if not args.apply:
            print("dry run; pass --apply to write")
            return

        for row, item, changes in updates:
            if "line" in changes:
                line = session.scalar(select(ProductLine).where(
                    ProductLine.manufacturer_id == row.manufacturer_id,
                    ProductLine.name == item["line"],
                ))
                if line is None:
                    line = ProductLine(manufacturer_id=row.manufacturer_id, name=item["line"])
                    session.add(line)
                    session.flush()
                row.product_line_id = line.id
            for field in ("work", "edition", "release_channel", "price", "release_date", "detail", "aliases"):
                if field in changes:
                    setattr(row, field, changes[field])

        for item in inserts:
            maker = makers[item["manufacturer"]]
            line = session.scalar(select(ProductLine).where(
                ProductLine.manufacturer_id == maker.id,
                ProductLine.name == item["line"],
            ))
            if line is None:
                line = ProductLine(manufacturer_id=maker.id, name=item["line"])
                session.add(line)
                session.flush()
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
                    aliases=";".join([item["alias"], *item["extra_aliases"]]),
                )
            )
        session.commit()
        print(f"updated {len(updates)}, inserted {len(inserts)}")


if __name__ == "__main__":
    main()
