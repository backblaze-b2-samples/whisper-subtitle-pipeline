"""Scoped caption library + subtitle-pipeline dashboard metrics.

`/library` is scoped to this app's own prefixes (source/ + captions/) — it
complements, never replaces, the full-bucket explorer at /files.
"""

from app.repo import list_files
from app.service.jobs import list_jobs
from app.service.pipeline import CAPTIONS_PREFIX
from app.service.upload import SOURCE_PREFIX
from app.types import LibraryEntry, PipelineStats
from app.types.formatting import humanize_bytes


def _captions_size() -> tuple[int, int]:
    """Return (total caption bytes, caption file count) under captions/."""
    files = list_files(prefix=CAPTIONS_PREFIX, max_keys=1000)
    # The manifest.json lives under captions/ too — count it as overhead, not
    # as a caption file, so the "caption files generated" metric is honest.
    caption_files = [f for f in files if not f.key.endswith("manifest.json")]
    total = sum(f.size_bytes for f in caption_files)
    return total, len(caption_files)


def get_library() -> list[LibraryEntry]:
    """Group each source video with the caption set derived from it."""
    sources = list_files(prefix=SOURCE_PREFIX, max_keys=1000)
    jobs = list_jobs()
    # Most recent succeeded/any job per source key wins for display.
    by_source: dict[str, object] = {}
    for job in jobs:
        if job.source_key not in by_source:
            by_source[job.source_key] = job

    entries: list[LibraryEntry] = []
    for src in sources:
        job = by_source.get(src.key)
        artifacts = list(job.artifacts) if job else []
        captions_size = sum(a.size_bytes for a in artifacts)
        entries.append(
            LibraryEntry(
                source_key=src.key,
                source_filename=src.filename,
                source_size_bytes=src.size_bytes,
                source_size_human=src.size_human,
                job_id=job.id if job else None,
                status=job.status if job else None,
                languages=list(job.languages) if job else [],
                artifacts=artifacts,
                captions_size_bytes=captions_size,
                captions_size_human=humanize_bytes(captions_size),
            )
        )
    return entries


def get_pipeline_stats() -> PipelineStats:
    """Headline dashboard metrics for the subtitle pipeline."""
    sources = list_files(prefix=SOURCE_PREFIX, max_keys=1000)
    source_size = sum(f.size_bytes for f in sources)
    captions_size, caption_files = _captions_size()

    jobs = list_jobs()
    succeeded = [j for j in jobs if j.status == "succeeded"]
    videos_processed = len({j.source_key for j in succeeded})
    languages = {lang for j in succeeded for lang in j.languages}

    ratio = round(captions_size / source_size, 3) if source_size else 0.0
    total = source_size + captions_size
    return PipelineStats(
        videos_processed=videos_processed,
        caption_files=caption_files,
        languages_covered=len(languages),
        source_size_bytes=source_size,
        source_size_human=humanize_bytes(source_size),
        captions_size_bytes=captions_size,
        captions_size_human=humanize_bytes(captions_size),
        derived_ratio=ratio,
        total_b2_size_bytes=total,
        total_b2_size_human=humanize_bytes(total),
    )
