"""Add the 78dm 无限维度「复仇女神 机械透明版」product.

The user asked to add this as a separate product even though
「复仇女神（机械透明版本）」 already exists. Only this row is written; the other
无限维度 products are untouched.

Default is a dry run; `--apply` inserts.
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

MANUFACTURER = "无限维度"
PAGE_URL = "https://acg.78dm.net/ct/446774.html"
KIT_NAME = "复仇女神 机械透明版"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        manufacturer = session.scalar(select(Manufacturer).where(Manufacturer.name == MANUFACTURER))
        if manufacturer is None:
            raise SystemExit(f"manufacturer not found: {MANUFACTURER}")
        existing = session.scalar(
            select(Product).where(
                Product.manufacturer_id == manufacturer.id,
                Product.kit_name == KIT_NAME,
            )
        )
        if existing is not None:
            print(f"{KIT_NAME} already exists ({existing.id}); nothing to do")
            return

        print("insert:", KIT_NAME)
        print(f"  manufacturer={MANUFACTURER} line=<none> code=<none>")
        print("  channel=regular edition=普通版 price=<none> release_date=<none>")
        print(f"  detail=78dm：{PAGE_URL}")

        if not args.apply:
            print("\ndry run; pass --apply to write")
            return

        session.add(
            Product(
                manufacturer_id=manufacturer.id,
                product_line_id=None,
                product_code=None,
                kit_name=KIT_NAME,
                work=None,
                release_channel="regular",
                edition="普通版",
                release_date=None,
                detail=f"78dm：{PAGE_URL}",
                source=PAGE_URL,
                price=None,
            )
        )
        session.commit()

    print("inserted 1")


if __name__ == "__main__":
    main()
