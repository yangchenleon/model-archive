"""Asset endpoints: one row per owned kit, plus bulk actions."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.models import Asset, AssetStateChange, Product
from app.schemas import (
    AssetCreate,
    AssetRead,
    AssetStateChangeRead,
    AssetUpdate,
    BulkAssetCreate,
    BulkStateUpdate,
)
from app.services import assets as service

router = APIRouter(tags=["assets"])


@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> Asset:
    """One owned kit. Buying the same kit twice creates two rows."""
    return service.create(session, payload)


@router.get("/assets", response_model=list[AssetRead])
def list_assets(
    state: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
    session: Session = Depends(get_session),
) -> list[Asset]:
    statement = (
        select(Asset)
        .options(selectinload(Asset.product), selectinload(Asset.tags))
        .order_by(Asset.created_at.desc(), Asset.code)
        .limit(limit)
    )
    if state and state != "all":
        statement = statement.where(Asset.state == state)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.join(Product).where(
            or_(Asset.code.ilike(term), Product.kit_name.ilike(term))
        )
    return list(session.scalars(statement))


@router.post("/assets/bulk", response_model=list[AssetRead], status_code=status.HTTP_201_CREATED)
def bulk_create_assets(payload: BulkAssetCreate, session: Session = Depends(get_session)) -> list[Asset]:
    """Backlog entry: register N products at once, each with an initial state."""
    return service.create_many(session, payload)


@router.post("/assets/bulk/state")
def bulk_update_state(payload: BulkStateUpdate, session: Session = Depends(get_session)) -> dict[str, int]:
    """One transition for many assets."""
    return service.change_many(session, payload)


@router.get("/assets/by-code/{code}", response_model=AssetRead)
def get_asset_by_code(code: str, session: Session = Depends(get_session)) -> Asset:
    """Typed or scanned from a sticker; accepts lower case and O/I/L for 0/1."""
    return service.find_by_code(session, code)


@router.get("/assets/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: UUID, session: Session = Depends(get_session)) -> Asset:
    return service.load(session, asset_id)


@router.patch("/assets/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: UUID, payload: AssetUpdate, session: Session = Depends(get_session)) -> Asset:
    """Field edits are silent; a state change also writes an audit row."""
    return service.update(session, asset_id, payload)


@router.get("/assets/{asset_id}/state-changes", response_model=list[AssetStateChangeRead])
def list_state_changes(asset_id: UUID, session: Session = Depends(get_session)) -> list[AssetStateChange]:
    return service.history(session, asset_id)


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    service.delete(session, asset_id)
    return {"deleted": str(asset_id)}
