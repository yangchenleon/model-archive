"""Add/supplement the three 哮星 HowlingStar 机神 kits.

Data sources: chaihezi product pages (星云/科拉达/仲裁者) plus the 78dm 科拉达
page. Existing 仲裁者 row is completed instead of duplicated.
Default is a dry run; `--apply` writes.
"""

from __future__ import annotations

import argparse
import os
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

MAKER = "哮星"
LINE = "机神"
MARK = "产品信息"

ITEMS = [
    {
        "name": "机神·星云",
        "code": None,
        "work": "交错核心",
        "price": "298元",
        "date": date(2023, 3, 1),
        "source": "https://www.chaihezi.com/node/271657",
        "aliases": "机神 星云;NEBULA;星云",
        "detail": """产品信息
来源: https://www.chaihezi.com/node/271657
出品: 哮星 HowlingStar × 交错核心
售价: 298元
预计出货: 2023年3月
全高: 约23cm
说明: 预涂装外甲、绿色透明件；外甲可全数拆卸还原骨架；配件含两把剃刀与专用步枪。""",
    },
    {
        "name": "科拉达",
        "code": None,
        "work": "交错战线",
        "price": "299元（预定）/339元（现货）",
        "date": date(2026, 6, 1),
        "source": "https://www.chaihezi.com/node/360329",
        "aliases": "机神 科拉达;COLADA;克拉达",
        "detail": """产品信息
来源: https://www.chaihezi.com/node/360329
78dm: https://acg.78dm.net/ct/439156.html
出品: 核诚治造 × 哮星 / 交错战线
定价: 299元（预定价）/339元（现货价）
预计: 2026年春季发货，2026年6月到货
全高: 约35cm；全装备长度50cm；机甲单体16cm
零件: 900+；11个灯组；预喷涂板件；PVC/ABS""",
    },
    {
        "name": "仲裁者",
        "code": "CZ-09B",
        "work": "交错战线",
        "price": "188元",
        "date": date(2026, 12, 1),
        "source": "https://www.chaihezi.com/node/378948",
        "aliases": "机神 仲裁者;Arbiter;CZ-09B",
        "detail": """产品信息
来源: https://www.chaihezi.com/node/378948
出品: 哮星 / 交错战线
编号: CZ-09B
售价: 188元（国内无销售）
预计到货: 2026年12月
全高: 约20cm
材质: PET/ABS；约790个零件，56板
说明: 双形态切换，人马型机体。""",
    },
]


def append_alias(existing: str | None, value: str) -> str:
    parts = [part.strip() for part in (existing or "").split(";") if part.strip()]
    if value not in parts:
        parts.append(value)
    return ";".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        maker = session.scalar(select(Manufacturer).where(Manufacturer.name == MAKER))
        if maker is None:
            maker = Manufacturer(name=MAKER, category="guomo", tier=3)
            session.add(maker)
            session.flush()
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
        for item in ITEMS:
            row = rows.get(item["name"])
            if row is None:
                inserts.append(item)
                continue
            changes = {}
            if row.product_line_id is None:
                changes["line"] = line
            if row.product_code is None and item["code"]:
                changes["product_code"] = item["code"]
            if row.work is None:
                changes["work"] = item["work"]
            if row.edition is None:
                changes["edition"] = "普通版"
            if row.release_channel is None:
                changes["release_channel"] = "regular"
            if not row.price and item["price"]:
                changes["price"] = item["price"]
            if row.release_date is None:
                changes["release_date"] = item["date"]
            if MARK not in (row.detail or ""):
                prefix = f"{row.detail.rstrip()}\n\n" if row.detail else ""
                changes["detail"] = prefix + item["detail"]
            aliases = row.aliases
            for alias in item["aliases"].split(";"):
                aliases = append_alias(aliases, alias)
            if aliases != (row.aliases or ""):
                changes["aliases"] = aliases
            if changes:
                updates.append((row, item, changes))

        print(f"updates {len(updates)}; inserts {len(inserts)}")
        for row, item, changes in updates:
            print(f"  UPDATE {row.kit_name} -> {sorted(changes)}")
        for item in inserts:
            print(f"  INSERT {item['name']} | {item['price']} | {item['date']} | line={LINE}")

        if not args.apply:
            print("dry run; pass --apply to write")
            return

        for row, item, changes in updates:
            if "line" in changes:
                row.product_line_id = line.id
            for field in ("product_code", "work", "edition", "release_channel", "price", "release_date", "detail", "aliases"):
                if field in changes:
                    setattr(row, field, changes[field])

        for item in inserts:
            session.add(
                Product(
                    manufacturer_id=maker.id,
                    product_line_id=line.id,
                    kit_name=item["name"],
                    product_code=item["code"],
                    work=item["work"],
                    edition="普通版",
                    release_channel="regular",
                    price=item["price"],
                    release_date=item["date"],
                    detail=item["detail"],
                    source=item["source"],
                    aliases=item["aliases"],
                )
            )
        session.commit()
        print(f"updated {len(updates)}, inserted {len(inserts)}")


if __name__ == "__main__":
    main()
