"""Export the database to the human-friendly CSV templates."""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
from app.db import SessionLocal
from app.models import Asset, AssetEvent, CatalogItem, CollectionTarget
ORIGIN = {"official": "官方/正版", "china_brand": "国模", "ko": "KO/翻模", "gk": "GK", "third_party": "第三方", "unknown": "待确认"}
STATUS = {"wanted": "想买", "ordered": "已预订", "owned_unbuilt": "待拼", "building": "拼装中", "built": "已拼", "to_sell": "待出售", "to_trade": "待置换", "sold": "已出售", "returned": "已退货", "review": "待确认"}
CONDITION = {"sealed": "未拆", "opened": "已拆", "complete": "完整", "incomplete": "缺件", "unknown": "待确认"}
DECISION = {"collect": "收", "consider": "考虑", "skip": "不收", "owned": "已拥有", "duplicate": "重复"}
CONFIDENCE = {"reported": "记录", "verified": "已核验", "uncertain": "待核验"}
EVENT = {"acquired": "购入", "opened": "开盒", "build_started": "开始拼装", "build_completed": "完成拼装", "listed": "挂出", "traded": "置换", "sold": "出售", "returned": "退货", "status_corrected": "状态修正", "note": "备注"}
CATALOG_HEADERS = ["厂商", "来源类型", "产品线", "比例", "模型名称", "版本/配色", "厂商编号", "对应机体/原型", "盒绘标识", "资料可信度", "来源备注"]
ASSET_HEADERS = ["厂商", "来源类型", "产品线", "比例", "模型名称", "版本/配色", "厂商编号", "当前状态", "盒况", "数量", "存放位置", "购入日期", "购入价格", "备注"]
TARGET_HEADERS = ["收藏分组", "厂商", "来源类型", "产品线", "比例", "模型名称", "版本/配色", "厂商编号", "收藏决定", "优先级", "原因", "规则版本"]
EVENT_HEADERS = ["厂商", "来源类型", "产品线", "比例", "模型名称", "版本/配色", "厂商编号", "存放位置", "事件", "日期", "变更前状态", "变更后状态", "来源备注", "附加信息"]
def catalog_row(item: CatalogItem) -> dict[str, object]:
    return {"厂商": item.manufacturer, "来源类型": ORIGIN[item.origin_type], "产品线": item.product_line or "", "比例": item.scale or "", "模型名称": item.kit_name, "版本/配色": item.variant_name or "", "厂商编号": item.manufacturer_code or "", "对应机体/原型": item.subject_name or "", "盒绘标识": item.box_art_key or "", "资料可信度": CONFIDENCE[item.confidence], "来源备注": item.source_note or ""}
def write(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows({header: row.get(header, "") for header in headers} for row in rows)
def main(directory: str) -> None:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as session:
        items = list(session.query(CatalogItem).order_by(CatalogItem.manufacturer, CatalogItem.product_line, CatalogItem.kit_name))
        item_by_id = {item.id: item for item in items}
        write(root / "catalog_items.csv", CATALOG_HEADERS, [catalog_row(item) for item in items])
        assets = list(session.query(Asset).order_by(Asset.created_at))
        asset_by_id = {asset.id: asset for asset in assets}
        asset_rows = []
        for asset in assets:
            row = catalog_row(item_by_id[asset.catalog_item_id])
            row.update({"当前状态": STATUS[asset.status], "盒况": CONDITION[asset.condition], "数量": asset.quantity, "存放位置": asset.storage_location or "", "购入日期": asset.acquired_on.isoformat() if asset.acquired_on else "", "购入价格": asset.purchase_price or "", "备注": asset.notes or ""})
            asset_rows.append(row)
        write(root / "assets.csv", ASSET_HEADERS, asset_rows)
        target_rows = []
        for target in session.query(CollectionTarget).order_by(CollectionTarget.collection_name):
            row = catalog_row(item_by_id[target.catalog_item_id])
            row.update({"收藏分组": target.collection_name, "收藏决定": DECISION[target.decision], "优先级": target.priority or "", "原因": target.reason or "", "规则版本": target.rule_version or ""})
            target_rows.append(row)
        write(root / "collection_targets.csv", TARGET_HEADERS, target_rows)
        event_rows = []
        for event in session.query(AssetEvent).order_by(AssetEvent.occurred_at):
            asset = asset_by_id[event.asset_id]
            row = catalog_row(item_by_id[asset.catalog_item_id])
            row.update({"存放位置": asset.storage_location or "", "事件": EVENT[event.event_type], "日期": event.occurred_at.isoformat(), "变更前状态": STATUS[event.from_status] if event.from_status else "", "变更后状态": STATUS[event.to_status] if event.to_status else "", "来源备注": event.source_note or "", "附加信息": json.dumps(event.metadata_json or {}, ensure_ascii=False)})
            event_rows.append(row)
        write(root / "asset_events.csv", EVENT_HEADERS, event_rows)
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.export_csv /app/data/drafts/current_snapshot_friendly")
    main(sys.argv[1])
