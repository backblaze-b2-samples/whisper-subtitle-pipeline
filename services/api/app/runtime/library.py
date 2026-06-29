"""Scoped caption library + subtitle-pipeline dashboard metric routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.service.jobs import caption_url
from app.service.library import get_library, get_pipeline_stats
from app.types import LibraryEntry, PipelineStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library", response_model=list[LibraryEntry])
async def library_endpoint():
    return get_library()


@router.get("/library/stats", response_model=PipelineStats)
async def pipeline_stats_endpoint():
    return get_pipeline_stats()


@router.get("/library/source-url")
async def source_url_endpoint(key: str):
    """Presigned URL for a source video (used by the <video> player)."""
    if not key.startswith("source/"):
        raise HTTPException(status_code=400, detail="Key not under source/")
    try:
        return {"url": caption_url(key)}
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to sign URL") from None
