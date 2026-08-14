"""Import human-friendly Chinese CSV templates without exposing database identifiers."""
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
def mapped(row: dict[str, str], field: str, mapping: dict[str, str], default: str | None = None) -> str | None:
    value = text(row, field)
    if value is None:
        return default
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
    manufacturer = text(row, "厂商")
    kit_name = text(row, "模型名称")
    if not manufacturer or not kit_name:
        raise ValueError("模型目录和资产清单都必须填写 厂商 与 模型名称")
    return {"manufacturer": manufacturer, "origin_type": mapped(row, "来源类型", ORIGIN, "unknown"), "product_line": text(row, "产品线"), "scale": text(row, "比例"), "kit_name": kit_name, "variant_name": text(row, "版本/配色"), "manufacturer_code": text(row, "厂商编号")}
def find_item(session, identity: dict[str, str | None]) -> CatalogItem | None:
    statement = select(CatalogItem)
    for field, value in identity.items():
        column = getattr(CatalogItem, field)
        statement = statement.where(column.is_(None) if value is None else column == value)
    item = session.scalar(statement)
    if item or identity["origin_type"] != "unknown":
        return item
    fallback = select(CatalogItem)
    for field, value in identity.items():
        if field == "origin_type":
            continue
        column = getattr(CatalogItem, field)
        fallback = fallback.where(column.is_(None) if value is None else column == value)
    matches = list(session.scalars(fallback))
    return matches[0] if len(matches) == 1 else None
def item_from_row(session, row: dict[str, str]) -> CatalogItem:
    identity = item_identity(row)
    item = find_item(session, identity)
    details = {"subject_name": text(row, "对应机体/原型"), "box_art_key": text(row, "盒绘标识"), "source_note": text(row, "来源备注"), "confidence": mapped(row, "资料可信度", CONFIDENCE, "reported")}
    if item:
        for field, value in details.items():
            if value is not None:
                setattr(item, field, value)
        return item
    item = CatalogItem(**identity, **details, catalog_key=f"catalog-{uuid4()}")
    session.add(item)
    session.flush()
    return item
def find_asset(session, item: CatalogItem, location: str | None) -> Asset | None:
    statement = select(Asset).where(Asset.catalog_item_id == item.id)
    statement = statement.where(Asset.storage_location.is_(None) if location is None else Asset.storage_location == location)
    matches = list(session.scalars(statement))
    if len(matches) <= 1:
        return matches[0] if matches else None
    raise ValueError(f"{item.kit_name} 在同一存放位置有多条资产；请等待界面版按复选框选择具体盒子")
def import_data(root: Path) -> dict[str, int]:
    rows = {name: read_csv(root / filename) for name, filename in FILES.items()}
    created = {"items": 0, "assets": 0, "collection_targets": 0, "events": 0}
    with SessionLocal.begin() as session:
        for row in rows["items"]:
            identity = item_identity(row)
            if not find_item(session, identity):
                created["items"] += 1
            item_from_row(session, row)
        for row in rows["assets"]:
            item = item_from_row(session, row)
            location = text(row, "存放位置")
            asset = find_asset(session, item, location)
            status_value = mapped(row, "当前状态", STATUS)
            if not status_value:
                raise ValueError("资产清单必须填写 当前状态")
            values = {"status": status_value, "condition": mapped(row, "盒况", CONDITION, "unknown"), "quantity": int(text(row, "数量") or "1"), "storage_location": location, "acquired_on": date.fromisoformat(text(row, "购入日期")) if text(row, "购入日期") else None, "purchase_price": Decimal(text(row, "购入价格")) if text(row, "购入价格") else None, "notes": text(row, "备注")}
            if asset:
                for field, value in values.items():
                    if value is not None:
                        setattr(asset, field, value)
            else:
                session.add(Asset(**values, catalog_item_id=item.id, asset_key=f"asset-{uuid4()}"))
                created["assets"] += 1
        for row in rows["targets"]:
            collection_name = text(row, "收藏分组")
            if not collection_name:
                continue
            item = item_from_row(session, row)
            target = session.scalar(select(CollectionTarget).where(CollectionTarget.collection_name == collection_name, CollectionTarget.catalog_item_id == item.id))
            values = {"decision": mapped(row, "收藏决定", DECISION, "consider"), "priority": int(text(row, "优先级")) if text(row, "优先级") else None, "reason": text(row, "原因"), "rule_version": text(row, "规则版本")}
            if target:
                for field, value in values.items():
                    if value is not None:
                        setattr(target, field, value)
            else:
                session.add(CollectionTarget(**values, collection_name=collection_name, catalog_item_id=item.id))
                created["collection_targets"] += 1
        for row in rows["events"]:
            item = item_from_row(session, row)
            asset = find_asset(session, item, text(row, "存放位置"))
            if not asset:
                raise ValueError(f"{item.kit_name} 没有可关联资产；先填写资产清单或暂时留空事件表")
            event_type = mapped(row, "事件", EVENT)
            if not event_type:
                raise ValueError("事件记录必须填写 事件")
            note = text(row, "来源备注")
            exists = session.scalar(select(AssetEvent).where(AssetEvent.asset_id == asset.id, AssetEvent.event_type == event_type, AssetEvent.source_note == note))
            if not exists:
                values = {"asset_id": asset.id, "event_type": event_type, "from_status": mapped(row, "变更前状态", STATUS), "to_status": mapped(row, "变更后状态", STATUS), "source_note": note, "metadata_json": json.loads(text(row, "附加信息") or "{}")}
                occurred_at = text(row, "日期")
                if occurred_at:
                    values["occurred_at"] = datetime.fromisoformat(occurred_at)
                session.add(AssetEvent(**values))
                created["events"] += 1
    return created
def main(directory: str) -> None:
    created = import_data(Path(directory))
    print("import complete: " + ", ".join(f"{name}={count}" for name, count in created.items()))
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.import_csv /app/data/drafts/current_snapshot")
    main(sys.argv[1])
