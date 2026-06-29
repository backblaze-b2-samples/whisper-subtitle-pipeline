"""Pydantic models for the Subtitle Job primary entity."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Finite option sets — kept here so the frontend selectors and backend
# validation share one source of truth (exposed via GET /jobs/options).
JobStatus = Literal["pending", "running", "succeeded", "failed"]
JobTask = Literal["transcribe", "translate"]
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]

# Curated language list for source/target selectors. "auto" = detect.
LANGUAGE_CHOICES: list[dict[str, str]] = [
    {"code": "auto", "label": "Auto-detect"},
    {"code": "en", "label": "English"},
    {"code": "es", "label": "Spanish"},
    {"code": "fr", "label": "French"},
    {"code": "de", "label": "German"},
    {"code": "pt", "label": "Portuguese"},
    {"code": "it", "label": "Italian"},
    {"code": "nl", "label": "Dutch"},
    {"code": "ja", "label": "Japanese"},
    {"code": "ko", "label": "Korean"},
    {"code": "zh", "label": "Chinese"},
    {"code": "ru", "label": "Russian"},
    {"code": "ar", "label": "Arabic"},
    {"code": "hi", "label": "Hindi"},
]

MODEL_CHOICES: list[ModelSize] = ["tiny", "base", "small", "medium", "large-v3"]


class CaptionArtifact(BaseModel):
    """A single derived caption file in B2 (SRT / VTT / transcript JSON)."""

    kind: Literal["srt", "vtt", "json"]
    language: str
    key: str
    size_bytes: int
    size_human: str


class JobCreate(BaseModel):
    """Payload to create (or, when editing, replace) a subtitle job."""

    source_key: str = Field(..., min_length=1)
    source_language: str = "auto"
    target_language: str = "en"
    model_size: ModelSize = "base"
    task: JobTask = "translate"


class Job(BaseModel):
    """A subtitle job — one transcription(+translation) of a source video."""

    id: str
    source_key: str
    source_filename: str
    source_language: str
    target_language: str
    model_size: ModelSize
    task: JobTask
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    # Detected language (filled in after a run) and the language codes that
    # actually have caption sets written to B2.
    detected_language: str | None = None
    languages: list[str] = Field(default_factory=list)
    artifacts: list[CaptionArtifact] = Field(default_factory=list)
    duration_seconds: float | None = None
    error: str | None = None
    # Coarse progress hint for the running state (0-100). Best-effort only.
    progress: int = 0


class JobOptions(BaseModel):
    """Finite option sets for the New Job / Edit Job selectors."""

    languages: list[dict[str, str]]
    models: list[ModelSize]
    tasks: list[str]
    default_model: ModelSize
