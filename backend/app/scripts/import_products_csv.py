"""Temporary importer for a product directory CSV."""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product
IDENTITY_FIELDS = ("manufacturer", "product_code", "origin_type", "product_line", "kit_name", "variant_name")
def text(row: dict[str, str], field: str) -> str | None:
    value = (row.get(field) or "").strip()
    return value or None
def required_text(row: dict[str, str], field: str) -> str:
    value = text(row, field)
    if value is None:
        raise ValueError(f"missing required field: {field}")
    return value
def identity(row: dict[str, str]) -> dict[str, str | None]:
    return {"manufacturer": text(row, "厂商"), "product_code": text(row, "产品编号"), "origin_type": text(row, "来源类型"), "product_line": text(row, "产品线"), "kit_name": required_text(row, "模型名称"), "variant_name": text(row, "版本/配色")}
def find_product(session, values: dict[str, str | None]) -> Product | None:
    statement = select(Product)
    for field in IDENTITY_FIELDS:
        value = values[field]
        column = getattr(Product, field)
        statement = statement.where(column.is_(None) if value is None else column == value)
    return session.scalar(statement)
def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            if None in row:
                raise ValueError(f"{path}:{row_number}: too many columns; quote text containing commas")
            if any((value or "").strip() for value in row.values()):
                rows.append({field: (value or "").strip() for field, value in row.items()})
        return rows
def import_products(path: Path, fallback_source: str | None = None) -> tuple[int, int]:
    created = 0
    updated = 0
    with SessionLocal.begin() as session:
        for row in read_csv(path):
            values = identity(row)
            detail = text(row, "详情")
            source = text(row, "资料来源") or fallback_source
            if source is None:
                raise ValueError("missing required field: 资料来源 (or use --source for legacy CSV)")
            product = find_product(session, values)
            if product:
                product.source = source
                product.detail = detail
                product.product_code = values["product_code"]
                updated += 1
            else:
                session.add(Product(**values, detail=detail, source=source))
                created += 1
    return created, updated
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--source", help="legacy CSV without the 资料来源 column")
    arguments = parser.parse_args()
    created, updated = import_products(Path(arguments.csv_path), arguments.source)
    print(f"import complete: created={created}, updated={updated}")
