"""Signature / device-resolution guards for the whisper engine.

These run with NO network and NO model download — they only exercise the
pure device/compute selection logic and the public function signature, so
CI stays fast and offline. The actual transcription is covered by the
end-to-end verify step (a real short video), not here.
"""

import inspect

from app.config import settings
from app.repo import whisper_engine


def test_transcribe_signature_is_stable():
    sig = inspect.signature(whisper_engine.transcribe)
    params = sig.parameters
    assert "audio_path" in params
    # Keyword-only knobs the service layer relies on.
    assert params["model_size"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["task"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["language"].kind == inspect.Parameter.KEYWORD_ONLY


def test_explicit_cpu_device(monkeypatch):
    monkeypatch.setattr(settings, "whisper_device", "cpu")
    assert whisper_engine._resolve_device() == "cpu"


def test_auto_device_falls_back_to_cpu_without_cuda(monkeypatch):
    """auto must never hard-require a GPU — no CUDA -> CPU."""
    monkeypatch.setattr(settings, "whisper_device", "auto")

    # Simulate no CUDA build / no devices.
    import sys
    import types

    fake_ct2 = types.ModuleType("ctranslate2")
    fake_ct2.get_cuda_device_count = lambda: 0
    monkeypatch.setitem(sys.modules, "ctranslate2", fake_ct2)

    assert whisper_engine._resolve_device() == "cpu"


def test_compute_type_auto_picks_int8_on_cpu(monkeypatch):
    monkeypatch.setattr(settings, "whisper_compute_type", "auto")
    assert whisper_engine._resolve_compute_type("cpu") == "int8"
    assert whisper_engine._resolve_compute_type("cuda") == "float16"
