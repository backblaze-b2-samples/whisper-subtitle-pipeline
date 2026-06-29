<!-- last_verified: 2026-06-29 -->
# Architecture

`whisper-subtitle-pipeline` transcribes and translates source videos on-device with faster-whisper and stores both the source media and the derived caption artifacts in a single Backblaze B2 bucket.

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with subtitle-pipeline metrics + storage breakdown
  - Subtitle Jobs (`/jobs`) — list + create form; detail (`/jobs/[id]`) with a video player + live VTT caption track, transcript artifacts, downloads, and run/edit/delete
  - Caption library (`/library`) — scoped explorer over `source/` + `captions/`
  - Source-video upload + full-bucket file browser
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for the Subtitle Job lifecycle, library, and dashboard metrics
  - faster-whisper transcription + NLLB-200 translation engines (on-device, in `repo/`)
  - B2 S3 integration via boto3 (single shared client, custom user agent)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. **The ML dependencies (faster-whisper for speech, NLLB-200 for translation, both on ctranslate2) are imported only in the `repo/` adapters `whisper_engine.py` and `translate_engine.py`** (lazily, inside functions) — contained exactly like the storage SDK
5. All boundary data uses Pydantic models (no raw dicts across layers)
6. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (Job, LibraryEntry, PipelineStats, FileMetadata, ...)
    config/                Settings loaded from environment (B2_* + WHISPER_*)
    repo/                  B2 S3 client (b2_client.py) + ML engines (whisper_engine.py, translate_engine.py)
    service/               Business logic (jobs, pipeline, subtitles, library, upload, files)
    runtime/               FastAPI route handlers (jobs, library, upload, files, health, metrics)
  tests/                   pytest tests (structural + unit + signature guards)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. All file keys validated against prefix allowlist.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - `source/<filename>` — uploaded source videos
  - `captions/<job_id>/{lang}.srt|.vtt|.transcript.json` — derived caption artifacts
  - `captions/manifest.json` — job/video index, the **system of record** for completed jobs
  - A small in-process registry tracks live (pending/running) job progress; it is lost on restart (see [docs/RELIABILITY.md](docs/RELIABILITY.md))
  - No application database

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, deletion, presigned URLs
- **No external AI provider.** Transcription runs **on-device** via faster-whisper; translation runs **on-device** via NLLB-200 (both on the CTranslate2 backend). Model weights download once from Hugging Face (public — no token). There is no second API key; B2 credentials only.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Upload source video**: Browser -> `POST /upload` (multipart) -> API validates video type -> repo `put_object` to `source/<filename>` -> response
- **Create + run a Subtitle Job** (primary pipeline):
  1. Browser -> `POST /jobs` -> service validates the `source/` key, writes a `pending` job to `captions/manifest.json`, and schedules it on a single-worker background executor; returns immediately.
  2. Worker: repo `download_to_path` pulls the source video from B2 to a temp file -> `whisper_engine.transcribe` runs faster-whisper on-device to get the source transcript -> for a translate job, `translate_engine.translate_segments` runs NLLB-200 on that transcript to produce the target-language text (timings preserved) -> `subtitles.py` renders SRT/VTT/JSON for each language -> repo `put_text` writes them to `captions/<job_id>/` -> manifest updated to `succeeded`.
  3. UI polls `GET /jobs/{id}` via TanStack Query `refetchInterval` while `running`, showing the generating-loader.
- **Read a job**: Browser -> `GET /jobs` / `GET /jobs/{id}` -> service merges live registry + manifest.
- **Edit a job**: Browser -> `PATCH /jobs/{id}` -> updates settings (does not auto-run).
- **Run / re-run**: Browser -> `POST /jobs/{id}/run` -> re-schedules on the worker.
- **Delete a job**: Browser -> `DELETE /jobs/{id}` -> repo `delete_prefix("captions/<job_id>/")` (scoped to that job only) + manifest entry removed.
- **Library / dashboard**: Browser -> `GET /library` / `GET /library/stats` -> service lists `source/` + `captions/` via `list_objects_v2` and joins the manifest.
- **Player & downloads**: Browser -> `GET /library/source-url` (video) + `GET /jobs/{id}/artifacts/url` (VTT track, SRT/JSON) -> repo `generate_presigned_url`.

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Job lifecycle routes: `services/api/app/runtime/jobs.py`
- Pipeline orchestration: `services/api/app/service/pipeline.py`
- Job store + manifest: `services/api/app/service/jobs.py`
- Subtitle formatters: `services/api/app/service/subtitles.py`
- faster-whisper adapter (speech ML import): `services/api/app/repo/whisper_engine.py`
- NLLB-200 translation adapter (text ML import): `services/api/app/repo/translate_engine.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`jobs.py`, `library.py`, `files.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Local Transcription](docs/features/transcription.md)
- [Translation](docs/features/translation.md)
- [Subtitle Export (SRT/VTT/JSON)](docs/features/subtitle-export.md)
- [Caption Library](docs/features/caption-library.md)
- [Dashboard](docs/features/dashboard.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
