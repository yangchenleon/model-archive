"""HTTP endpoints.

Routers stay thin: they validate transport concerns (paths, query params) and
delegate every rule to ``app.services``. Ordering note: fixed segments such as
``/assets/bulk`` must be declared before ``/assets/{asset_id}``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import assets, media, products, review, tags

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(products.router)
api_router.include_router(review.router)
api_router.include_router(assets.router)
api_router.include_router(tags.router)
api_router.include_router(media.router)

__all__ = ["api_router"]
