from __future__ import annotations
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import get_session
from app.models import Asset, AssetEvent, CatalogItem, CollectionTarget
from app.schemas import AssetCreate, AssetEventCreate, AssetEventRead, AssetRead, AssetStatusUpdate, CatalogItemCreate, CatalogItemRead, CollectionTargetCreate, CollectionTargetRead
app = FastAPI(title="Model Archive API", version="0.1.0")
def missing(entity: str, key: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity} not found: {key}")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
@app.post("/api/v1/items", response_model=CatalogItemRead, status_code=status.HTTP_201_CREATED)
def create_item(payload: CatalogItemCreate, session: Session = Depends(get_session)) -> CatalogItem:
    if session.scalar(select(CatalogItem).where(CatalogItem.catalog_key == payload.catalog_key)):
        raise HTTPException(status_code=409, detail="catalog_key already exists")
    item = CatalogItem(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
@app.get("/api/v1/items", response_model=list[CatalogItemRead])
def list_items(search: str | None = None, limit: int = Query(default=100, le=500), session: Session = Depends(get_session)) -> list[CatalogItem]:
    statement = select(CatalogItem).order_by(CatalogItem.kit_name).limit(limit)
    if search:
        statement = statement.where(CatalogItem.kit_name.ilike(f"%{search}%"))
    return list(session.scalars(statement))
@app.post("/api/v1/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> Asset:
    if session.scalar(select(Asset).where(Asset.asset_key == payload.asset_key)):
        raise HTTPException(status_code=409, detail="asset_key already exists")
    item = session.scalar(select(CatalogItem).where(CatalogItem.catalog_key == payload.catalog_key))
    if not item:
        raise missing("catalog item", payload.catalog_key)
    asset = Asset(**payload.model_dump(exclude={"catalog_key"}), catalog_item_id=item.id)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
@app.get("/api/v1/assets", response_model=list[AssetRead])
def list_assets(asset_status: str | None = None, limit: int = Query(default=100, le=500), session: Session = Depends(get_session)) -> list[Asset]:
    statement = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
    if asset_status:
        statement = statement.where(Asset.status == asset_status)
    return list(session.scalars(statement))
@app.patch("/api/v1/assets/{asset_key}", response_model=AssetRead)
def update_asset_status(asset_key: str, payload: AssetStatusUpdate, session: Session = Depends(get_session)) -> Asset:
    asset = session.scalar(select(Asset).where(Asset.asset_key == asset_key))
    if not asset:
        raise missing("asset", asset_key)
    previous = asset.status
    asset.status = payload.status
    session.add(AssetEvent(asset_id=asset.id, event_type="status_corrected", from_status=previous, to_status=payload.status, source_note=payload.note))
    session.commit()
    session.refresh(asset)
    return asset
@app.post("/api/v1/collection-targets", response_model=CollectionTargetRead, status_code=status.HTTP_201_CREATED)
def create_collection_target(payload: CollectionTargetCreate, session: Session = Depends(get_session)) -> CollectionTarget:
    item = session.scalar(select(CatalogItem).where(CatalogItem.catalog_key == payload.catalog_key))
    if not item:
        raise missing("catalog item", payload.catalog_key)
    target = CollectionTarget(**payload.model_dump(exclude={"catalog_key"}), catalog_item_id=item.id)
    session.add(target)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="collection target already exists")
    session.refresh(target)
    return target
@app.get("/api/v1/collection-targets", response_model=list[CollectionTargetRead])
def list_collection_targets(collection_name: str | None = None, session: Session = Depends(get_session)) -> list[CollectionTarget]:
    statement = select(CollectionTarget).order_by(CollectionTarget.collection_name, CollectionTarget.priority)
    if collection_name:
        statement = statement.where(CollectionTarget.collection_name == collection_name)
    return list(session.scalars(statement))
@app.post("/api/v1/asset-events", response_model=AssetEventRead, status_code=status.HTTP_201_CREATED)
def create_asset_event(payload: AssetEventCreate, session: Session = Depends(get_session)) -> AssetEvent:
    asset = session.scalar(select(Asset).where(Asset.asset_key == payload.asset_key))
    if not asset:
        raise missing("asset", payload.asset_key)
    event = AssetEvent(**payload.model_dump(exclude={"asset_key"}, exclude_none=True), asset_id=asset.id)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event
@app.get("/api/v1/asset-events", response_model=list[AssetEventRead])
def list_asset_events(asset_key: str | None = None, session: Session = Depends(get_session)) -> list[AssetEvent]:
    statement = select(AssetEvent).order_by(AssetEvent.occurred_at.desc())
    if asset_key:
        asset = session.scalar(select(Asset).where(Asset.asset_key == asset_key))
        if not asset:
            raise missing("asset", asset_key)
        statement = statement.where(AssetEvent.asset_id == asset.id)
    return list(session.scalars(statement))
