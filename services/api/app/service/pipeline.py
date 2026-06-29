"""Subtitle pipeline orchestration: B2 -> faster-whisper -> SRT/VTT/JSON -> B2.

The heavy work runs on a single-worker background executor. `POST /jobs`
enqueues a `pending` job and returns immediately; the UI polls
`GET /jobs/{id}` while it's `running`.
"""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.repo import download_to_path, put_text, transcribe, translate_segments
from app.service.subtitles import to_srt, to_transcript_json, to_vtt
from app.types import CaptionArtifact, Job
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

CAPTIONS_PREFIX = "captions/"

# Single background worker — keeps the demo's resource use predictable and
# matches the documented restart caveat (in-flight jobs are lost on restart).
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")


def captions_prefix(job_id: str) -> str:
    return f"{CAPTIONS_PREFIX}{job_id}/"


def _write_artifacts(
    job_id: str, language: str, result: dict
) -> list[CaptionArtifact]:
    """Write SRT + VTT + transcript JSON for one language to B2."""
    prefix = captions_prefix(job_id)
    segments = result["segments"]
    duration = result.get("duration_seconds", 0.0)
    files = {
        "srt": (f"{prefix}{language}.srt", "text/plain", to_srt(segments)),
        "vtt": (f"{prefix}{language}.vtt", "text/vtt", to_vtt(segments)),
        "json": (
            f"{prefix}{language}.transcript.json",
            "application/json",
            to_transcript_json(
                segments, language=language, duration_seconds=duration
            ),
        ),
    }
    artifacts: list[CaptionArtifact] = []
    for kind, (key, content_type, body) in files.items():
        size = put_text(key, body, content_type)
        artifacts.append(
            CaptionArtifact(
                kind=kind,  # type: ignore[arg-type]
                language=language,
                key=key,
                size_bytes=size,
                size_human=humanize_bytes(size),
            )
        )
    return artifacts


def run_job(job: Job, *, on_update) -> Job:
    """Execute a job end-to-end. `on_update(job)` persists progress.

    Returns the job in its terminal state (`succeeded` or `failed`).
    """
    suffix = os.path.splitext(job.source_key)[1] or ".mp4"
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="whisper-src-", suffix=suffix)
    os.close(tmp_fd)
    artifacts: list[CaptionArtifact] = []
    languages: list[str] = []
    detected: str | None = None
    duration: float | None = None
    try:
        job.status = "running"
        job.progress = 10
        on_update(job)

        logger.info("Job %s: downloading %s from B2", job.id, job.source_key)
        download_to_path(job.source_key, tmp_path)
        job.progress = 25
        on_update(job)

        # 1. Transcribe in the source language.
        logger.info("Job %s: transcribing (model=%s)", job.id, job.model_size)
        src = transcribe(
            tmp_path,
            model_size=job.model_size,
            task="transcribe",
            language=job.source_language,
        )
        detected = src["detected_language"]
        duration = src["duration_seconds"]
        source_lang = detected or "source"
        artifacts += _write_artifacts(job.id, source_lang, src)
        languages.append(source_lang)
        job.progress = 65
        on_update(job)

        # 2. Optionally translate the transcript into the target language.
        # Whisper's own `translate` task can only target English, so we
        # translate the transcribed text with NLLB-200 (see
        # repo/translate_engine.py) and keep the source timings.
        if (
            job.task == "translate"
            and detected
            and job.target_language not in (detected, "auto", "", None)
        ):
            target_lang = job.target_language
            logger.info(
                "Job %s: translating %s -> %s", job.id, detected, target_lang
            )
            translated = translate_segments(
                src["segments"],
                source_language=detected,
                target_language=target_lang,
            )
            tgt = {"segments": translated, "duration_seconds": duration}
            artifacts += _write_artifacts(job.id, target_lang, tgt)
            languages.append(target_lang)

        job.artifacts = artifacts
        job.languages = languages
        job.detected_language = detected
        job.duration_seconds = duration
        job.status = "succeeded"
        job.progress = 100
        on_update(job)
        logger.info("Job %s: succeeded (%d artifacts)", job.id, len(artifacts))
    except Exception as e:
        logger.error("Job %s failed: %s", job.id, e, exc_info=True)
        job.status = "failed"
        job.error = str(e)
        job.progress = 0
        on_update(job)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return job


def submit(job: Job, *, on_update) -> None:
    """Schedule a job on the background worker (non-blocking)."""
    _executor.submit(run_job, job, on_update=on_update)


def warm_compute_type() -> str:
    """Report the resolved compute device hint (for diagnostics)."""
    return settings.whisper_device
