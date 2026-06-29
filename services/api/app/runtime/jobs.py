"""Subtitle Job routes — full CRUD + run lifecycle for the primary entity."""

import logging

from fastapi import APIRouter, HTTPException

from app.service.jobs import (
    JobNotFoundError,
    JobValidationError,
    caption_url,
    create_job,
    delete_job,
    get_job,
    get_options,
    list_jobs,
    run_job,
    update_job,
)
from app.types import Job, JobCreate, JobOptions

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle(fn, *args):
    try:
        return fn(*args)
    except JobValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/jobs/options", response_model=JobOptions)
async def job_options_endpoint():
    return get_options()


@router.get("/jobs", response_model=list[Job])
async def list_jobs_endpoint():
    return list_jobs()


@router.post("/jobs", response_model=Job)
async def create_job_endpoint(payload: JobCreate):
    job = _handle(create_job, payload)
    logger.info("Job created: id=%s source=%s", job.id, job.source_key)
    return job


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_endpoint(job_id: str):
    return _handle(get_job, job_id)


@router.patch("/jobs/{job_id}", response_model=Job)
async def update_job_endpoint(job_id: str, payload: JobCreate):
    return _handle(update_job, job_id, payload)


@router.post("/jobs/{job_id}/run", response_model=Job)
async def run_job_endpoint(job_id: str):
    job = _handle(run_job, job_id)
    logger.info("Job re-run: id=%s", job.id)
    return job


@router.delete("/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    _handle(delete_job, job_id)
    logger.info("Job deleted: id=%s", job_id)
    return {"deleted": True, "id": job_id}


@router.get("/jobs/{job_id}/artifacts/url")
async def artifact_url_endpoint(job_id: str, key: str):
    # Scope the presigned URL to this job's own caption prefix.
    if not key.startswith(f"captions/{job_id}/"):
        raise HTTPException(status_code=400, detail="Key not in this job's prefix")
    try:
        return {"url": caption_url(key)}
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to sign URL") from None
