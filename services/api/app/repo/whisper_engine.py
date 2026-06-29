"""faster-whisper transcription/translation engine adapter.

This is the single place the heavy ML dependency lives. The engine runs
**on-device** — no second API key, B2 credentials only. CTranslate2 has no
Apple-MPS backend, so device auto-detect resolves CUDA -> CPU (Apple Silicon
correctly lands on CPU int8). The app never hard-requires a GPU.
"""

import functools
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_device() -> str:
    """Pick a device: explicit override, else auto-detect CUDA -> CPU.

    There is no MPS branch on purpose — CTranslate2 (faster-whisper's
    backend) has no Apple-MPS support, so Apple Silicon falls back to CPU.
    """
    configured = (settings.whisper_device or "auto").lower()
    if configured in ("cpu", "cuda"):
        return configured
    # auto: prefer CUDA when a working CUDA build + device is present.
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        logger.info("CUDA not available; using CPU for transcription")
    return "cpu"


def _resolve_compute_type(device: str) -> str:
    configured = (settings.whisper_compute_type or "auto").lower()
    if configured != "auto":
        return configured
    return "float16" if device == "cuda" else "int8"


@functools.lru_cache(maxsize=4)
def _load_model(model_size: str):
    """Load (and cache) a WhisperModel for a given size.

    Weights download from Hugging Face on first use — Whisper models are
    public, so no token is required.
    """
    from faster_whisper import WhisperModel

    device = _resolve_device()
    compute_type = _resolve_compute_type(device)
    logger.info(
        "Loading faster-whisper model=%s device=%s compute_type=%s",
        model_size,
        device,
        compute_type,
    )
    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        cpu_threads=max(1, settings.whisper_worker_threads),
    )


def transcribe(
    audio_path: str,
    *,
    model_size: str,
    task: str = "transcribe",
    language: str | None = None,
) -> dict:
    """Run faster-whisper on a local media file.

    Returns a dict with `detected_language` and a list of `segments`, each
    `{start, end, text}` (seconds). `task="translate"` translates speech to
    English; for non-English targets we transcribe in the source language
    (callers handle target selection at the service layer).
    """
    model = _load_model(model_size)
    segments_iter, info = model.transcribe(
        audio_path,
        task=task,
        language=None if (language in (None, "", "auto")) else language,
        vad_filter=True,
        word_timestamps=False,
    )
    segments = [
        {"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()}
        for seg in segments_iter
    ]
    return {
        "detected_language": info.language,
        "duration_seconds": float(info.duration),
        "segments": segments,
    }
