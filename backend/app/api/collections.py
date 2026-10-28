"""Collection endpoints: a list of existing products plus derived progress."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Collection
from app.schemas import (
    CollectionBulkAdd,
    CollectionBulkAddResult,
    CollectionBulkRemove,
    CollectionBulkRemoveResult,
    CollectionCreate,
    CollectionItemCreate,
    CollectionItemList,
    CollectionItemRead,
    CollectionItemUpdate,
    CollectionRead,
    CollectionStats,
    CollectionUpdate,
)
from app.services import collections as service

router = APIRouter(tags=["collections"])


def _read(collection: Collection, stats: CollectionStats) -> CollectionRead:
    return CollectionRead(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        status=collection.status,
        started_on=collection.started_on,
        target_on=collection.target_on,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        stats=stats,
    )


def _item(view: service.ItemView) -> CollectionItemRead:
    product = view.product
    roll = view.roll
    return CollectionItemRead(
        id=view.item.id,
        product_id=product.id,
        name=product.kit_name,
        manufacturer=product.manufacturer,
        product_line=product.product_line,
        product_code=product.product_code,
        note=view.item.note,
        owned=roll.owned > 0,
        built=roll.built > 0,
        sold_only=roll.owned == 0 and roll.sold > 0,
        asset_count=roll.owned,
        asset_states=roll.states,
        sold_count=roll.sold,
    )


@router.get("/collections", response_model=list[CollectionRead])
def list_collections(
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[CollectionRead]:
    return [_read(collection, stats) for collection, stats in service.list_with_stats(session, status, q, limit)]


@router.post("/collections", response_model=CollectionRead, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate, session: Session = Depends(get_session)) -> CollectionRead:
    collection = service.create(session, payload)
    _, stats = service.get_with_stats(session, collection.id)
    return _read(collection, stats)


@router.get("/collections/{collection_id}", response_model=CollectionRead)
def get_collection(collection_id: UUID, session: Session = Depends(get_session)) -> CollectionRead:
    collection, stats = service.get_with_stats(session, collection_id)
    return _read(collection, stats)


@router.patch("/collections/{collection_id}", response_model=CollectionRead)
def update_collection(
    collection_id: UUID,
    payload: CollectionUpdate,
    session: Session = Depends(get_session),
) -> CollectionRead:
    collection = service.update(session, collection_id, payload)
    _, stats = service.get_with_stats(session, collection.id)
    return _read(collection, stats)


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: UUID, session: Session = Depends(get_session)) -> dict[str, str | int]:
    removed = service.delete(session, collection_id)
    return {"deleted": str(collection_id), "items": removed}


@router.get("/collections/{collection_id}/items", response_model=CollectionItemList)
def list_items(
    collection_id: UUID,
    state: str = "all",
    q: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> CollectionItemList:
    total, views = service.list_items(session, collection_id, state, q, limit, offset)
    return CollectionItemList(total=total, items=[_item(view) for view in views])


@router.post(
    "/collections/{collection_id}/items",
    response_model=CollectionItemRead,
    status_code=status.HTTP_201_CREATED,
)
def add_item(
    collection_id: UUID,
    payload: CollectionItemCreate,
    session: Session = Depends(get_session),
) -> CollectionItemRead:
    return _item(service.add_item(session, collection_id, payload.product_id))


@router.post("/collections/{collection_id}/items/bulk", response_model=CollectionBulkAddResult)
def bulk_add_items(
    collection_id: UUID,
    payload: CollectionBulkAdd,
    session: Session = Depends(get_session),
) -> CollectionBulkAddResult:
    result = service.add_many(session, collection_id, payload)
    return CollectionBulkAddResult(**result)


@router.post("/collections/{collection_id}/items/bulk-remove", response_model=CollectionBulkRemoveResult)
def bulk_remove_items(
    collection_id: UUID,
    payload: CollectionBulkRemove,
    session: Session = Depends(get_session),
) -> CollectionBulkRemoveResult:
    result = service.remove_many(session, collection_id, payload)
    return CollectionBulkRemoveResult(**result)


@router.patch("/collections/{collection_id}/items/{item_id}", response_model=CollectionItemRead)
def update_item(
    collection_id: UUID,
    item_id: UUID,
    payload: CollectionItemUpdate,
    session: Session = Depends(get_session),
) -> CollectionItemRead:
    return _item(service.update_item(session, collection_id, item_id, payload))


@router.delete("/collections/{collection_id}/items/{item_id}")
def delete_item(
    collection_id: UUID,
    item_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    service.remove_item(session, collection_id, item_id)
    return {"deleted": str(item_id)}
