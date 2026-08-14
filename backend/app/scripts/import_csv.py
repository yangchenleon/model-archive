"""Temporary strict importer for human-friendly Chinese CSV templates."""
from __future__ import annotations
import csv
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Asset, AssetEvent, CatalogItem, CollectionTarget
FILES = {"items": "catalog_items.csv", "assets": "assets.csv", "targets": "collection_targets.csv", "events": "asset_events.csv"}
ORIGIN = {"官方/正版": "official", "正版": "official", "国模": "china_brand", "KO/翻模": "ko", "GK": "gk", "第三方": "third_party", "待确认": "unknown"}
STATUS = {"想买": "wanted", "已预订": "ordered", "待拼": "owned_unbuilt", "拼装中": "building", "已拼": "built", "待出售": "to_sell", "待置换": "to_trade", "已出售": "sold", "已退货": "returned", "待确认": "review"}
CONDITION = {"未拆": "sealed", "已拆": "opened", "完整": "complete", "缺件": "incomplete", "待确认": "unknown"}
DECISION = {"收": "collect", "考虑": "consider", "不收": "skip", "已拥有": "owned", "重复": "duplicate"}
CONFIDENCE = {"记录": "reported", "已核验": "verified", "待核验": "uncertain"}
EVENT = {"购入": "acquired", "开盒": "opened", "开始拼装": "build_started", "完成拼装": "build_completed", "挂出": "listed", "置换": "traded", "出售": "sold", "退货": "returned", "状态修正": "status_corrected", "备注": "note"}
def text(row: dict[str, str], field: str) -> str | None:
    value = (row.get(field) or "").strip()
    return value or None
def required_text(row: dict[str, str], field: str) -> str:
    value = text(row, field)
    if value is None:
        raise ValueError(f"missing required field: {field}")
    return value
def mapped(row: dict[str, str], field: str, mapping: dict[str, str], required: bool = False) -> str | None:
    value = text(row, field)
    if value is None:
        if required:
            raise ValueError(f"missing required field: {field}")
        return None
    if value not in mapping:
        raise ValueError(f"{field} has an unsupported value: {value}")
    return mapping[value]
def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            if None in row:
                raise ValueError(f"{path}:{row_number}: too many columns; quote text containing commas")
            if any((value or "").strip() for value in row.values()):
                rows.append({field: (value or "").strip() for field, value in row.items()})
        return rows
def item_identity(row: dict[str, str]) -> dict[str, str | None]:
    return {"manufacturer": required_text(row, "厂商"), "origin_type": mapped(row, "来源类型", ORIGIN, required=True), "product_line": text(row, "产品线"), "scale": text(row, "比例"), "kit_name": required_text(row, "模型名称"), "variant_name": text(row, "版本/配色"), "manufacturer_code": text(row, "厂商编号")}
def find_item(session, identity: dict[str, str | None]) -> CatalogItem | None:
    statement = select(CatalogItem)
    for field, value in identity.items():
        column = getattr(CatalogItem, field)
        statement = statement.where(column.is_(None) if value is None else column == value)
    return session.scalar(statement)
def import_catalog_row(session, row: dict[str, str]) -> tuple[CatalogItem, bool]:
    identity = item_identity(row)
    details = {"subject_name": text(row, "对应机体/原型"), "box_art_key": text(row, "盒绘标识"), "source_note": text(row, "来源备注"), "confidence": mapped(row, "资料可信度", CONFIDENCE, required=True)}
    item = find_item(session, identity)
    if item:
        for field, value in details.items():
            setattr(item, field, value)
        return item, False
    item = CatalogItem(**identity, **details, catalog_key=f"catalog-{uuid4()}")
    session.add(item)
    session.flush()
    return item, True
def resolve_catalog(session, row: dict[str, str]) -> CatalogItem:
    item = find_item(session, item_identity(row))
    if not item:
        raise ValueError("catalog item not found; import catalog_items.csv first or correct the identifying fields")
    return item
def only_asset_for_catalog(session, item: CatalogItem) -> Asset | None:
    assets = list(session.scalars(select(Asset).where(Asset.catalog_item_id == item.id)))
    if len(assets) > 1:
        raise ValueError(f"{item.kit_name} has multiple asset records; temporary CSV import cannot choose one")
    return assets[0] if assets else None
def asset_values(row: dict[str, str]) -> dict:
    quantity = int(required_text(row, "数量"))
    if quantity < 1:
        raise ValueError("数量 must be greater than zero")
    acquired_on = text(row, "购入日期")
    purchase_price = text(row, "购入价格")
    return {"status": mapped(row, "当前状态", STATUS, required=True), "condition": mapped(row, "盒况", CONDITION, required=True), "quantity": quantity, "storage_location": text(row, "存放位置"), "acquired_on": date.fromisoformat(acquired_on) if acquired_on else None, "purchase_price": Decimal(purchase_price) if purchase_price else None, "notes": text(row, "备注")}
def same_values(record: Asset, values: dict) -> bool:
    return all(getattr(record, field) == value for field, value in values.items())
def import_data(root: Path) -> dict[str, int]:
    rows = {name: read_csv(root / filename) for name, filename in FILES.items()}
    created = {"items": 0, "assets": 0, "collection_targets": 0, "events": 0}
    with SessionLocal.begin() as session:
        for row in rows["items"]:
            _, was_created = import_catalog_row(session, row)
            created["items"] += was_created
        for row in rows["assets"]:
            item = resolve_catalog(session, row)
            values = asset_values(row)
            existing = only_asset_for_catalog(session, item)
            if existing:
                if not same_values(existing, values):
                    raise ValueError(f"{item.kit_name} already has an asset with different data; update it in the future UI, not through this temporary importer")
                continue
            session.add(Asset(**values, catalog_item_id=item.id, asset_key=f"asset-{uuid4()}"))
            created["assets"] += 1
        for row in rows["targets"]:
            collection_name = required_text(row, "收藏分组")
            item = resolve_catalog(session, row)
            values = {"decision": mapped(row, "收藏决定", DECISION, required=True), "priority": int(text(row, "优先级")) if text(row, "优先级") else None, "reason": text(row, "原因"), "rule_version": text(row, "规则版本")}
            target = session.scalar(select(CollectionTarget).where(CollectionTarget.collection_name == collection_name, CollectionTarget.catalog_item_id == item.id))
            if target:
                if any(getattr(target, field) != value for field, value in values.items()):
                    raise ValueError(f"collection target already exists with different data: {collection_name} / {item.kit_name}")
                continue
            session.add(CollectionTarget(**values, collection_name=collection_name, catalog_item_id=item.id))
            created["collection_targets"] += 1
        for row in rows["events"]:
            item = resolve_catalog(session, row)
            asset = only_asset_for_catalog(session, item)
            if not asset:
                raise ValueError(f"{item.kit_name} has no asset record; import the asset first")
            occurred_at = datetime.fromisoformat(required_text(row, "日期"))
            event_type = mapped(row, "事件", EVENT, required=True)
            note = text(row, "来源备注")
            exists = session.scalar(select(AssetEvent).where(AssetEvent.asset_id == asset.id, AssetEvent.event_type == event_type, AssetEvent.occurred_at == occurred_at, AssetEvent.source_note == note))
            if exists:
                continue
            session.add(AssetEvent(asset_id=asset.id, event_type=event_type, occurred_at=occurred_at, from_status=mapped(row, "变更前状态", STATUS), to_status=mapped(row, "变更后状态", STATUS), source_note=note, metadata_json=json.loads(text(row, "附加信息") or "{}")))
            created["events"] += 1
    return created
def main(directory: str) -> None:
    created = import_data(Path(directory))
    print("import complete: " + ", ".join(f"{name}={count}" for name, count in created.items()))
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.import_csv /app/data/drafts/current_snapshot_friendly")
    main(sys.argv[1])
