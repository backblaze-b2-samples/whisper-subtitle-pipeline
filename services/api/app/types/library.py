"""Pydantic models for the scoped caption library + dashboard metrics."""

from pydantic import BaseModel, Field

from app.types.jobs import CaptionArtifact


class LibraryEntry(BaseModel):
    """A source video grouped with the caption sets derived from it."""

    source_key: str
    source_filename: str
    source_size_bytes: int
    source_size_human: str
    job_id: str | None = None
    status: str | None = None
    languages: list[str] = Field(default_factory=list)
    artifacts: list[CaptionArtifact] = Field(default_factory=list)
    captions_size_bytes: int = 0
    captions_size_human: str = "0.0 B"


class PipelineStats(BaseModel):
    """Headline subtitle-pipeline dashboard metrics."""

    videos_processed: int
    caption_files: int
    languages_covered: int
    source_size_bytes: int
    source_size_human: str
    captions_size_bytes: int
    captions_size_human: str
    # The headline value prop: derived caption bytes per source byte.
    derived_ratio: float
    total_b2_size_bytes: int
    total_b2_size_human: str
