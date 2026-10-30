"""Import the scraped 78dm MG manifest into PostgreSQL.

Default is a dry run. Use --apply to replace the current 万代/MG and 万代/MGEX
products with the manifest.

The 78dm MG page mixes channels, editions, works and accessories. All rows are
kept on line=MG except the EXtreme section, which is line=MGEX. Unreleased
reference products are excluded. Edition is the official section label; craft is
a single common finish/process value inferred from the edition/name.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
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

LINE_BY_SECTION = {"EXtreme": "MGEX"}

CHANNEL_BY_SECTION = {
    "普通版": "regular",
    "网络限定版": "pb",
    "其他限定版": "limited",
    "一番赏": "lottery",
    "HD配色": "limited",
    "重力战线": "limited",
    "官方豪华版": "limited",
    "官方特别版": "limited",
    "特殊武器配件": "limited",
    "高达30周年透明配件版": "event",
    "限定透明版": "limited",
    "限定电镀透明版": "limited",
    "限定电镀版": "limited",
    "限量版RX-79[G]特别涂装版": "limited",
    "竞赛奖品版": "event",
    "水晶版": "limited",
    "彩色电镀版": "limited",
    "圣战士丹拜因": "regular",
    "机动警察": "regular",
    "一年战争版": "limited",
    "EXtreme": None,
}

EDITION_BY_SECTION = {
    "EXtreme": "EXtreme",
    "HD配色": "HD配色",
    "官方豪华版": "豪华版",
    "官方特别版": "特别版",
    "特殊武器配件": "配置包",
    "高达30周年透明配件版": "30周年透明配件版",
    "限定透明版": "限定透明版",
    "限定电镀透明版": "限定电镀透明版",
    "限定电镀版": "限定电镀版",
    "限量版RX-79[G]特别涂装版": "特别涂装版",
    "竞赛奖品版": "竞赛奖品版",
    "水晶版": "水晶版",
    "彩色电镀版": "彩色电镀版",
    "一年战争版": "一年战争版",
}

WORK_BY_SECTION = {
    "重力战线": "重力战线",
    "一年战争版": "一年战争",
    "圣战士丹拜因": "圣战士丹拜因",
    "机动警察": "机动警察",
}

EXCLUDED_SECTIONS = {"往期未商品化参考出品"}

CRAFT_PATTERNS = (
    ("clear_plated", ("电镀透明",)),
    ("color_plated", ("彩色电镀",)),
    ("clear", ("彩透",)),
    ("transparent", ("透明",)),
    ("plated", ("电镀",)),
    ("pearl", ("珍珠", "珠光")),
    ("metallic", ("金属",)),
    ("coating", ("涂层", "涂装")),
    ("matte", ("消光",)),
    ("crystal", ("水晶",)),
    ("luminous", ("夜光",)),
)


def parse_release_date(value: str) -> date | None:
    match = re.search(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?", value or "")
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3) or 1))
        except ValueError:
            return None
    match = re.search(r"(\d{4})年", value or "")
    if match:
        try:
            return date(int(match.group(1)), 1, 1)
        except ValueError:
            return None
    return None


def strip_code(name: str) -> str:
    return re.sub(r"^\s*MG\s*\d+\s+", "", name or "", flags=re.I).strip()


def infer_craft(*values: str) -> str | None:
    text = " ".join(value for value in values if value)
    for craft, patterns in CRAFT_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return craft
    return None


def build_detail(product: dict, line: str) -> str:
    fields = [
        ("78dm", product.get("url", "")),
        ("78dm名称", product.get("name", "")),
        ("来源分类", product.get("source_category", "")),
        ("版本", product.get("version", "")),
        ("发售时间", product.get("release_date", "")),
        ("比例", product.get("scale", "")),
        ("人物名", product.get("character", "")),
        ("材料", product.get("material", "")),
        ("规格", product.get("specification", "")),
        ("玩具分类", product.get("toy_category", "")),
        ("line", line),
    ]
    return "\n".join(f"{key}: {value}" for key, value in fields if value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="imports/78dm/2328/products.json")
    parser.add_argument("--manufacturer", default="万代")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    data = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
    raw = data["products"]
    if not raw:
        raise SystemExit("empty manifest")

    rows: list[dict] = []
    for product in raw:
        section = product.get("source_category", "")
        if section in EXCLUDED_SECTIONS:
            continue
        line = LINE_BY_SECTION.get(section, "MG")
        base_name = strip_code(product.get("name", ""))
        if not base_name:
            raise SystemExit(f"empty name for {product.get('id')}")
        rows.append({
            "id": uuid4(),
            "source": product,
            "base_name": base_name,
            "line": line,
            "section": section,
            "channel": CHANNEL_BY_SECTION.get(section),
            "edition": EDITION_BY_SECTION.get(section),
            "work": WORK_BY_SECTION.get(section),
            "craft": infer_craft(product.get("edition", ""), section, base_name),
            "release_date": parse_release_date(product.get("release_date", "")),
        })

    # Disambiguate duplicate display names. Keep the regular one unsuffixed when
    # possible; otherwise suffix every duplicate with its official edition label.
    by_name: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_name[(row["line"], row["base_name"])].append(row)
    for (line, base_name), group in by_name.items():
        if len(group) == 1:
            group[0]["kit_name"] = base_name
            continue
        normal = next((row for row in group if row["channel"] == "regular"), None)
        for row in group:
            if row is normal:
                row["kit_name"] = base_name
            else:
                suffix = row["edition"] or row["section"]
                row["kit_name"] = f"{base_name}（{suffix}）"
        # Last-resort uniqueness for same section/edition duplicates.
        seen: set[str] = set()
        for row in group:
            if row["kit_name"] in seen:
                row["kit_name"] = f"{row['kit_name']}（{row['source']['id']}）"
            seen.add(row["kit_name"])

    names = [(row["line"], row["kit_name"]) for row in rows]
    if len(names) != len(set(names)):
        dupes = [name for name, count in Counter(names).items() if count > 1]
        raise SystemExit(f"duplicate names remain: {dupes[:10]}")

    print("raw", len(raw), "importable", len(rows))
    print("lines", Counter(row["line"] for row in rows))
    print("channels", Counter(row["channel"] for row in rows))
    print("works", Counter(row["work"] for row in rows))
    print("editions", Counter(row["edition"] for row in rows).most_common(12))
    print("crafts", Counter(row["craft"] for row in rows))
    print("duplicates resolved", [(line, name, len(group)) for (line, name), group in by_name.items() if len(group) > 1][:10])

    if not args.apply:
        print("dry run; pass --apply to replace 万代/MG and 万代/MGEX")
        return

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == args.manufacturer))
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {args.manufacturer}")

        lines: dict[str, ProductLine] = {}
        for line_name in sorted({row["line"] for row in rows}):
            line = session.scalar(
                select(ProductLine).where(
                    ProductLine.manufacturer_id == manufacturer.id,
                    ProductLine.name == line_name,
                )
            )
            if line is None:
                line = ProductLine(manufacturer_id=manufacturer.id, name=line_name)
                session.add(line)
                session.flush()
            lines[line_name] = line

        old_ids = list(session.scalars(
            select(Product.id).where(
                Product.manufacturer_id == manufacturer.id,
                Product.product_line_id.in_([line.id for line in lines.values()]),
            )
        ))
        print(f"replacing {len(old_ids)} existing MG/MGEX products")
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
            session.execute(delete(Product).where(Product.id.in_(old_ids)))

        prepared = []
        for row in rows:
            source = row["source"]
            prepared.append({
                "id": row["id"],
                "manufacturer_id": manufacturer.id,
                "product_line_id": lines[row["line"]].id,
                "product_code": source.get("code") or None,
                "kit_name": row["kit_name"],
                "work": row["work"],
                "release_channel": row["channel"],
                "edition": row["edition"],
                "craft": row["craft"],
                "release_date": row["release_date"],
                "detail": build_detail(source, row["line"]),
                "source": source.get("url", ""),
                "price": source.get("price") or None,
            })
        session.execute(Product.__table__.insert(), prepared)
        session.commit()

    print(f"inserted {len(prepared)} products")


if __name__ == "__main__":
    main()
