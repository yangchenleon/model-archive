"""Model Archive API entry point.

Everything with a rule lives in ``app.services``; everything with a URL lives in
``app.api``. This module only assembles them.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router
from app.services.errors import AppError

app = FastAPI(title="Model Archive API", version="0.6.0")


@app.exception_handler(AppError)
async def domain_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Services speak domain errors; HTTP status codes are decided here, once."""
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
