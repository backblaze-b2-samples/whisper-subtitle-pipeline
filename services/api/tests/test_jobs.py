"""Job lifecycle tests — no network, no model load.

The B2 repo functions and the background pipeline are monkeypatched so the
manifest store + CRUD logic can be exercised in isolation.
"""

from datetime import UTC, datetime

import pytest

from app.service import jobs as jobs_service
from app.types import FileMetadata, JobCreate


@pytest.fixture
def fake_b2(monkeypatch):
    """In-memory stand-in for the B2 repo functions the job store uses."""
    store: dict[str, str] = {}
    sources = {
        "source/clip.mp4": FileMetadata(
            key="source/clip.mp4",
            filename="clip.mp4",
            folder="source/",
            size_bytes=1024,
            size_human="1.0 KB",
            content_type="video/mp4",
            uploaded_at=datetime.now(UTC),
            url=None,
        )
    }
    monkeypatch.setattr(jobs_service, "get_text", lambda key: store.get(key))

    def _put_text(key, body, content_type):
        store[key] = body
        return len(body.encode("utf-8"))

    monkeypatch.setattr(jobs_service, "put_text", _put_text)
    monkeypatch.setattr(jobs_service, "get_file_metadata", lambda key: sources.get(key))
    monkeypatch.setattr(jobs_service, "delete_prefix", lambda prefix: 0)
    # Don't actually run the model — capture submissions instead.
    submitted: list = []
    monkeypatch.setattr(
        jobs_service.pipeline,
        "submit",
        lambda job, on_update: submitted.append(job),
    )
    # Reset the in-process registry between tests.
    jobs_service._live.clear()
    return {"store": store, "submitted": submitted}


def test_create_job_persists_and_enqueues(fake_b2):
    job = jobs_service.create_job(
        JobCreate(source_key="source/clip.mp4", target_language="es")
    )
    assert job.status == "pending"
    assert job.source_filename == "clip.mp4"
    # Auto-run was scheduled.
    assert fake_b2["submitted"] and fake_b2["submitted"][0].id == job.id
    # Persisted to the manifest in B2.
    assert "captions/manifest.json" in fake_b2["store"]
    assert jobs_service.get_job(job.id).id == job.id


def test_create_job_rejects_unknown_source(fake_b2):
    with pytest.raises(jobs_service.JobValidationError):
        jobs_service.create_job(JobCreate(source_key="source/missing.mp4"))


def test_create_job_rejects_non_source_prefix(fake_b2):
    with pytest.raises(jobs_service.JobValidationError):
        jobs_service.create_job(JobCreate(source_key="uploads/clip.mp4"))


def test_edit_job_updates_settings_without_rerun(fake_b2):
    job = jobs_service.create_job(JobCreate(source_key="source/clip.mp4"))
    fake_b2["submitted"].clear()
    updated = jobs_service.update_job(
        job.id,
        JobCreate(source_key="source/clip.mp4", model_size="small", task="transcribe"),
    )
    assert updated.model_size == "small"
    assert updated.task == "transcribe"
    # Editing must NOT auto-run.
    assert fake_b2["submitted"] == []


def test_delete_job_removes_from_manifest(fake_b2):
    job = jobs_service.create_job(JobCreate(source_key="source/clip.mp4"))
    jobs_service.delete_job(job.id)
    with pytest.raises(jobs_service.JobNotFoundError):
        jobs_service.get_job(job.id)


def test_options_expose_finite_choices(fake_b2):
    opts = jobs_service.get_options()
    assert "large-v3" in opts.models
    codes = {c["code"] for c in opts.languages}
    assert "auto" in codes and "en" in codes
