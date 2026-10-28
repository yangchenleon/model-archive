"""Media endpoints: the review page's inline video and the print page's QR."""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

import segno
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse

router = APIRouter(tags=["media"])

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "outputs/daily_reports"))
VIDEO_ID = re.compile(r"^[A-Za-z0-9]+$")
DATE = re.compile(r"^\d{8}$")


@router.get("/media/{video_id}")
def media(video_id: str, date: str | None = None) -> FileResponse:
    """Serve the downloaded mp4 so the review page can play it inline."""
    if not VIDEO_ID.match(video_id):
        raise HTTPException(status_code=404, detail="视频不存在")
    pattern = (
        f"{date}_{video_id}/video/{video_id}.mp4"
        if date and DATE.match(date)
        else f"*_{video_id}/video/{video_id}.mp4"
    )
    matches = sorted(MEDIA_ROOT.glob(pattern))
    if not matches:
        raise HTTPException(status_code=404, detail="本地视频未下载")
    return FileResponse(
        matches[-1], media_type="video/mp4", headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/qr")
def qr(data: str, scale: int = Query(default=8, le=20)) -> Response:
    """Standalone SVG so the print page needs no font bundling and no client lib."""
    symbol = segno.make(data, error="m")
    buffer = io.BytesIO()
    # An <img src> needs the xmlns declaration that segno's inline output omits.
    symbol.save(buffer, kind="svg", scale=scale, border=2)
    return Response(content=buffer.getvalue(), media_type="image/svg+xml")
