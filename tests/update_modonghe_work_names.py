"""Fill 摩动核 work=星甲魂将传 and prepend the 星宿·称号 prefix to product names.

Blind-box lines (我是大英雄·第1弹/第2弹) are left untouched, as are 赤热五星
products that already carry a work. Mass-produced kits (威远式, 铁浮屠) and
洞渊主 have no 星宿 title in public sources, so only their work is filled.

Default is a dry run; `--apply` writes.
"""

from __future__ import annotations

import argparse
import os
import sys
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

MANUFACTURER = "摩动核"
WORK = "星甲魂将传"
BLIND_BOX_LINES = {"我是大英雄·第1弹", "我是大英雄·第2弹"}

# 星宿 / 宫位 + 称号, keyed by the character name the current kit_name starts with.
PREFIXES = {
    "白起": "天暴星·琥珀炎黄",
    "曹仁": "天速星·玉罗刹",
    "敖丙": "地会星·寒龙子",
    "哪吒": "天英星·三坛海会",
    "赵云": "天佑星·龙胆虎将",
    "干将": "地威星·封刃灵",
    "魔礼青": "天剑星·魔神四将",
    "吕布": "摇光宫·破军星君",
    "典韦": "地猛星·逐虎恶来",
    "马超": "天雄星·锦盔虎将",
    "霍去病": "天捷星·骠骑冠军",
    "岳飞": "天魁星·武穆神鹏",
    "闻仲": "天立星·雷声普化",
    "项羽": "玉衡宫·廉贞星君",
}
PREFIX_KEYS = sorted(PREFIXES, key=len, reverse=True)


def prefix_for(kit_name: str) -> str:
    for key in PREFIX_KEYS:
        if (
            kit_name == key
            or kit_name.startswith(f"{key} ")
            or kit_name.startswith(f"{key}·")
            or kit_name.startswith(f"{key}（")
        ):
            return PREFIXES[key]
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == MANUFACTURER))
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {MANUFACTURER}")
        rows = list(
            session.scalars(
                select(Product)
                .where(Product.manufacturer_id == manufacturer.id)
                .order_by(Product.kit_name)
            )
        )

        work_updates: list[Product] = []
        name_updates: list[tuple[Product, str]] = []
        for row in rows:
            line = row.product_line_ref.name if row.product_line_ref else None
            if line in BLIND_BOX_LINES:
                continue
            if not row.work:
                work_updates.append(row)
            prefix = prefix_for(row.kit_name)
            if prefix and not row.kit_name.startswith(prefix + "·"):
                name_updates.append((row, f"{prefix}·{row.kit_name}"))

        names = {}
        for row, new_name in name_updates:
            line = row.product_line_ref.name if row.product_line_ref else None
            key = (line, new_name)
            if key in names:
                print(f"WARNING duplicate name: {line} / {new_name} ({row.kit_name} & {names[key]})")
            names[key] = row.kit_name

        print(f"work -> {WORK}: {len(work_updates)}")
        for row in work_updates:
            line = row.product_line_ref.name if row.product_line_ref else "-"
            print(f"  [{line}] {row.kit_name}")

        print(f"\nrenamed: {len(name_updates)}")
        for row, new_name in name_updates:
            print(f"  {row.kit_name} -> {new_name}")

        titled_prefixes = tuple(f"{value}·" for value in PREFIXES.values())
        no_prefix = [
            row.kit_name
            for row in rows
            if (row.product_line_ref.name if row.product_line_ref else None) not in BLIND_BOX_LINES
            and row.work != "赤热五星"
            and not row.kit_name.startswith(titled_prefixes)
        ]
        print(f"\nno 星宿 prefix in sources ({len(no_prefix)}): {no_prefix}")

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        for row in work_updates:
            row.work = WORK
        for row, new_name in name_updates:
            row.kit_name = new_name
        session.commit()

    print(f"updated work={len(work_updates)}, renamed={len(name_updates)}")


if __name__ == "__main__":
    main()
