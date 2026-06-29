<!-- last_verified: 2026-06-29 -->
# Feature: Local Transcription

## Purpose
Produce segment-timestamped transcripts from source videos entirely on-device with faster-whisper — no per-minute SaaS fees and no second API key.

## Deployment
`local` — the engine runs on the host. Device is auto-detected (CUDA → CPU); CTranslate2 has no Apple-MPS backend, so Apple Silicon falls back to CPU `int8`. The app never hard-requires a GPU.

## Used By
- UI: `/jobs` (New Job form, task "Transcribe only" or "Transcribe + Translate")
- API: `POST /jobs`, `POST /jobs/{id}/run`
- Job: single-worker background executor in `service/pipeline.py`

## Core Functions
- `services/api/app/repo/whisper_engine.py` — `transcribe()`, `_resolve_device()`, `_resolve_compute_type()`, `_load_model()`
- `services/api/app/service/pipeline.py` — `run_job()` orchestration

## Inputs
- `audio_path`: local file path (the source video, downloaded from B2)
- `model_size`: `tiny|base|small|medium|large-v3` (per-job; default `base`)
- `language`: source language code or `auto` (detect)

## Outputs
- dict with `detected_language`, `duration_seconds`, and `segments` (`{start, end, text}`)
- side effect: model weights download from Hugging Face on first use (public, no token)

## Flow
1. `download_to_path` streams the `source/` video to a temp file
2. `_load_model(model_size)` loads (and caches) a `WhisperModel` on the resolved device
3. faster-whisper transcribes with VAD filtering; segments are normalized to plain dicts
4. The pipeline hands segments to the subtitle formatters

## Edge Cases
- No CUDA available → CPU `int8` (auto)
- Model not cached → first run downloads weights (slower)
- Unreadable / corrupt media → exception captured on the job (`status=failed`, `error` set)

## Verification
- Test files: `services/api/tests/test_whisper_engine.py` (signature + device-resolution guards, offline)
- End-to-end: a real short clip is transcribed during the verify step (model load + CTranslate2 inference, not mocked)
- Quick verify command: `pnpm test:api`
- Pass criteria: signature guards pass; a real clip yields at least one transcribed segment

## Related Docs
- [Translation](translation.md)
- [Subtitle Export](subtitle-export.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
