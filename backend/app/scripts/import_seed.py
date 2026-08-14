"""Import a local, Git-ignored personal inventory JSON file."""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Asset, AssetEvent, CatalogItem, CollectionTarget
def upsert(session, model, key_column, values):
    existing = session.scalar(select(model).where(key_column == values[key_column.key]))
    if existing:
        for field, value in values.items():
            setattr(existing, field, value)
        return existing, False
    instance = model(**values)
    session.add(instance)
    session.flush()
    return instance, True
def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
def main(seed_path: str) -> None:
    seed = load_json(Path(seed_path))
    created = {"items": 0, "assets": 0, "collection_targets": 0, "events": 0}
    with SessionLocal.begin() as session:
        items: dict[str, CatalogItem] = {}
        for raw in seed.get("items", []):
            item, was_created = upsert(session, CatalogItem, CatalogItem.catalog_key, raw)
            items[item.catalog_key] = item
            created["items"] += was_created
        for raw in seed.get("assets", []):
            values = raw.copy()
            catalog_key = values.pop("catalog_key")
            item = items.get(catalog_key) or session.scalar(select(CatalogItem).where(CatalogItem.catalog_key == catalog_key))
            if not item:
                raise ValueError(f"unknown catalog_key in assets: {catalog_key}")
            values["catalog_item_id"] = item.id
            _, was_created = upsert(session, Asset, Asset.asset_key, values)
            created["assets"] += was_created
        for raw in seed.get("collection_targets", []):
            values = raw.copy()
            catalog_key = values.pop("catalog_key")
            item = items.get(catalog_key) or session.scalar(select(CatalogItem).where(CatalogItem.catalog_key == catalog_key))
            if not item:
                raise ValueError(f"unknown catalog_key in collection_targets: {catalog_key}")
            target = session.scalar(select(CollectionTarget).where(CollectionTarget.collection_name == values["collection_name"], CollectionTarget.catalog_item_id == item.id))
            if target:
                for field, value in values.items():
                    setattr(target, field, value)
            else:
                session.add(CollectionTarget(**values, catalog_item_id=item.id))
                created["collection_targets"] += 1
        for raw in seed.get("events", []):
            values = raw.copy()
            asset_key = values.pop("asset_key")
            if isinstance(values.get("occurred_at"), str):
                values["occurred_at"] = datetime.fromisoformat(values["occurred_at"])
            asset = session.scalar(select(Asset).where(Asset.asset_key == asset_key))
            if not asset:
                raise ValueError(f"unknown asset_key in events: {asset_key}")
            exists = session.scalar(select(AssetEvent).where(AssetEvent.asset_id == asset.id, AssetEvent.event_type == values["event_type"], AssetEvent.source_note == values.get("source_note")))
            if not exists:
                session.add(AssetEvent(**values, asset_id=asset.id))
                created["events"] += 1
    print("import complete: " + ", ".join(f"{name}={count}" for name, count in created.items()))
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.import_seed /app/data/seed/initial_snapshot.json")
    main(sys.argv[1])
