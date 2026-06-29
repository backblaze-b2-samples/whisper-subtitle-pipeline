"""Subtitle Job store + lifecycle (create / read / edit / delete / run).

System of record for completed jobs is `captions/manifest.json` in B2. A
small in-process registry tracks live progress for jobs that are currently
pending/running (those are lost on restart — see docs/RELIABILITY.md).
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from threading import Lock

from app.config import settings
from app.repo import delete_prefix, get_file_metadata, get_presigned_url, get_text, put_text
from app.service import pipeline
from app.types import Job, JobCreate, JobOptions
from app.types.jobs import LANGUAGE_CHOICES, MODEL_CHOICES

logger = logging.getLogger(__name__)

MANIFEST_KEY = "captions/manifest.json"

# In-process registry of live jobs (pending/running). Completed jobs are
# read back from the B2 manifest, which is the durable system of record.
_live: dict[str, Job] = {}
_lock = Lock()


class JobNotFoundError(Exception):
    def __init__(self, detail: str = "Job not found"):
        self.detail = detail
        super().__init__(detail)


class JobValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


# --- Manifest (durable store in B2) ---


def _load_manifest() -> dict[str, Job]:
    raw = get_text(MANIFEST_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Manifest is not valid JSON; treating as empty")
        return {}
    jobs: dict[str, Job] = {}
    for entry in data.get("jobs", []):
        try:
            job = Job(**entry)
            jobs[job.id] = job
        except Exception:
            logger.warning("Skipping malformed manifest entry")
    return jobs


def _save_manifest(jobs: dict[str, Job]) -> None:
    payload = {
        "updated_at": _now().isoformat(),
        "jobs": [json.loads(j.model_dump_json()) for j in jobs.values()],
    }
    put_text(MANIFEST_KEY, json.dumps(payload, indent=2), "application/json")


def _persist(job: Job) -> None:
    """Upsert a job into the live registry and the durable manifest."""
    with _lock:
        job.updated_at = _now()
        _live[job.id] = job
    manifest = _load_manifest()
    manifest[job.id] = job
    _save_manifest(manifest)


# --- Public API ---


def get_options() -> JobOptions:
    return JobOptions(
        languages=LANGUAGE_CHOICES,
        models=list(MODEL_CHOICES),
        tasks=["transcribe", "translate"],
        default_model=settings.whisper_model,  # type: ignore[arg-type]
    )


def list_jobs() -> list[Job]:
    """Merge durable (manifest) + live jobs, newest first."""
    merged = _load_manifest()
    with _lock:
        for job_id, job in _live.items():
            merged[job_id] = job
    return sorted(merged.values(), key=lambda j: j.created_at, reverse=True)


def get_job(job_id: str) -> Job:
    with _lock:
        if job_id in _live:
            return _live[job_id]
    manifest = _load_manifest()
    if job_id not in manifest:
        raise JobNotFoundError()
    return manifest[job_id]


def _validate_source(source_key: str) -> str:
    if not source_key.startswith("source/"):
        raise JobValidationError("Source must be a video under the source/ prefix")
    meta = get_file_metadata(source_key)
    if not meta:
        raise JobValidationError(f"Source video '{source_key}' not found in B2")
    return meta.filename


def create_job(payload: JobCreate) -> Job:
    """Create a job, persist it as pending, and auto-run it."""
    filename = _validate_source(payload.source_key)
    now = _now()
    job = Job(
        id=uuid.uuid4().hex[:12],
        source_key=payload.source_key,
        source_filename=filename,
        source_language=payload.source_language,
        target_language=payload.target_language,
        model_size=payload.model_size,
        task=payload.task,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    _persist(job)
    pipeline.submit(job, on_update=_persist)
    return job


def update_job(job_id: str, payload: JobCreate) -> Job:
    """Edit a job's settings (does not auto-run; user re-runs explicitly)."""
    job = get_job(job_id)
    filename = _validate_source(payload.source_key)
    job.source_key = payload.source_key
    job.source_filename = filename
    job.source_language = payload.source_language
    job.target_language = payload.target_language
    job.model_size = payload.model_size
    job.task = payload.task
    _persist(job)
    return job


def run_job(job_id: str) -> Job:
    """(Re-)run a job's transcription on the background worker."""
    job = get_job(job_id)
    job.status = "pending"
    job.progress = 0
    job.error = None
    _persist(job)
    pipeline.submit(job, on_update=_persist)
    return job


def delete_job(job_id: str) -> None:
    """Delete a job and its caption artifacts (scoped to this job's prefix)."""
    job = get_job(job_id)
    # Scoped delete — only ever removes captions/<job_id>/*.
    delete_prefix(pipeline.captions_prefix(job.id))
    with _lock:
        _live.pop(job_id, None)
    manifest = _load_manifest()
    manifest.pop(job_id, None)
    _save_manifest(manifest)


def caption_url(key: str) -> str:
    """Presigned URL for a caption artifact / source video (preview)."""
    return get_presigned_url(key)
