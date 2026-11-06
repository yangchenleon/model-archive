"""Split 圣斯基 EVA 超可动拼装盲盒端 into its 7 known blind-box variants.

Official lineup (SOSKILL product page, 2026-01): 初号机 / 初号机觉醒[隐藏款] /
零号机 / 二号机 / Mark.06 / 八号机 / 第四使徒. One inner box has 6 pieces.

Default is a dry run; `--apply` deletes the 端盒 row (only when unreferenced)
and inserts the 7 variant rows.
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

from sqlalchemy import func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Asset, CollectionItem, Manufacturer, Product, ProductLine, ReviewItem  # noqa: E402

SET_NAME = "EVA 超可动拼装盲盒端"
MAKER = "圣斯基"
LINE = "新世纪福音战士"
SOURCE = "https://acg.78dm.net/ct/439169.html"
OFFICIAL = "https://www.soskilltoys.com/item/OTctMA"
VARIANTS = [
    ("初号机", "超可动拼装盲盒", False),
    ("零号机", "超可动拼装盲盒", False),
    ("二号机", "超可动拼装盲盒", False),
    ("Mark.06", "超可动拼装盲盒", False),
    ("八号机", "超可动拼装盲盒", False),
    ("第四使徒", "超可动拼装盲盒", False),
    ("初号机觉醒（隐藏款）", "超可动拼装盲盒（隐藏款）", True),
]


def build_detail(variant: str, hidden: bool) -> str:
    lines = [
        ("78dm", SOURCE),
        ("78dm名称", SET_NAME),
        ("版本", "普通版"),
        ("发售时间", "2026年01月"),
        ("材料", "塑料"),
        ("玩具分类", "塑料拼装模型"),
        ("来源分类", "综合拼装系列"),
        ("官方页面", OFFICIAL),
        ("官方配置", "初号机 / 初号机觉醒[隐藏款] / 零号机 / 二号机 / Mark.06 / 八号机 / 第四使徒"),
        ("整盒", "6 只；全套 7 款，含隐藏款"),
        ("款式", variant + ("（隐藏款）" if hidden else "")),
    ]
    return "\n".join(f"{key}: {value}" for key, value in lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        maker = session.scalar(select(Manufacturer).where(Manufacturer.name == MAKER))
        if maker is None:
            raise SystemExit(f"manufacturer not found: {MAKER}")
        line = session.scalar(
            select(ProductLine).where(
                ProductLine.manufacturer_id == maker.id,
                ProductLine.name == LINE,
            )
        )
        if line is None:
            raise SystemExit(f"line not found: {MAKER} / {LINE}")
        target = session.scalar(
            select(Product).where(
                Product.manufacturer_id == maker.id,
                Product.kit_name == SET_NAME,
            )
        )
        if target is None:
            existing = list(session.scalars(
                select(Product).where(
                    Product.manufacturer_id == maker.id,
                    Product.kit_name.like("EVA 超可动拼装盲盒 %"),
                )
            ))
            if len(existing) == 7:
                print("already split into 7 variants; nothing to do")
                return
            raise SystemExit(f"product not found: {SET_NAME}")

        references = {
            "assets": session.scalar(select(func.count()).select_from(Asset).where(Asset.product_id == target.id)) or 0,
            "collection_items": session.scalar(select(func.count()).select_from(CollectionItem).where(CollectionItem.product_id == target.id)) or 0,
            "review_items": session.scalar(select(func.count()).select_from(ReviewItem).where(ReviewItem.product_id == target.id)) or 0,
        }
        print(f"target: {SET_NAME} ({target.id}) refs={references}")
        print(f"will delete 1 row, insert {len(VARIANTS)} variants")
        for variant, edition, hidden in VARIANTS:
            print(f"  {variant} | {edition} | 79元 | 2026-01-01")
        if any(references.values()):
            raise SystemExit("target is referenced; refusing to delete")
        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        session.delete(target)
        session.flush()
        for variant, edition, hidden in VARIANTS:
            session.add(
                Product(
                    manufacturer_id=maker.id,
                    product_line_id=line.id,
                    kit_name=f"EVA 超可动拼装盲盒 {variant}",
                    work=LINE,
                    edition=edition,
                    release_channel="regular",
                    price="79元",
                    release_date=date(2026, 1, 1),
                    detail=build_detail(variant, hidden),
                    source=SOURCE,
                    aliases=variant,
                )
            )
        session.commit()
        print("deleted 1, inserted 7")


if __name__ == "__main__":
    main()
