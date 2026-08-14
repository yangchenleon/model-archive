"""Temporary strict importer for the product directory CSV."""
from __future__ import annotations
import csv
import sys
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product
ORIGIN = {"官方/正版": "official", "正版": "official", "国模": "china_brand", "KO/翻模": "ko", "GK": "gk", "第三方": "third_party", "待确认": "unknown"}
CONFIDENCE = {"记录": "reported", "已核验": "verified", "待核验": "uncertain"}
IDENTITY_FIELDS = ("manufacturer", "origin_type", "product_line", "scale", "kit_name", "variant_name", "manufacturer_code")
def text(row: dict[str, str], field: str) -> str | None:
    value = (row.get(field) or "").strip()
    return value or None
def required_text(row: dict[str, str], field: str) -> str:
    value = text(row, field)
    if value is None:
        raise ValueError(f"missing required field: {field}")
    return value
def mapped(row: dict[str, str], field: str, mapping: dict[str, str]) -> str:
    value = required_text(row, field)
    if value not in mapping:
        raise ValueError(f"{field} has an unsupported value: {value}")
    return mapping[value]
def identity(row: dict[str, str]) -> dict[str, str | None]:
    return {"manufacturer": required_text(row, "厂商"), "origin_type": mapped(row, "来源类型", ORIGIN), "product_line": text(row, "产品线"), "scale": text(row, "比例"), "kit_name": required_text(row, "模型名称"), "variant_name": text(row, "版本/配色"), "manufacturer_code": text(row, "厂商编号")}
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
def import_products(path: Path) -> tuple[int, int]:
    created = 0
    updated = 0
    with SessionLocal.begin() as session:
        for row in read_csv(path):
            values = identity(row)
            details = {"subject_name": text(row, "对应机体/原型"), "box_art_key": text(row, "盒绘标识"), "detail": text(row, "详情"), "confidence": mapped(row, "资料可信度", CONFIDENCE)}
            product = find_product(session, values)
            if product:
                for field, value in details.items():
                    setattr(product, field, value)
                updated += 1
            else:
                session.add(Product(**values, **details))
                created += 1
    return created, updated
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.import_products_csv /app/data/drafts/products.csv")
    created, updated = import_products(Path(sys.argv[1]))
    print(f"import complete: created={created}, updated={updated}")
