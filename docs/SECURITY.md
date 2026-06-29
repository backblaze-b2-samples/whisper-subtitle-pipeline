<!-- last_verified: 2026-06-29 -->
# Security

Security principles and implementation for the whisper-subtitle-pipeline.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/PATCH/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4. The S3 endpoint is derived from `B2_REGION`.
- **Client -> B2**: Presigned URLs (10-min expiry). Source-video and caption-track URLs are issued for inline player rendering; SRT/JSON downloads open in a new tab.

## Upload Validation (source videos)

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against a **video-only** allowlist (MP4, MOV, MKV, WebM, AVI)
- Chunked streaming with size enforcement (2 GB default)
- Empty file rejection

## Key Validation & Presigned-URL Scoping

- Empty keys rejected; path-traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- **Job artifact URLs are prefix-scoped**: `GET /jobs/{id}/artifacts/url` only signs keys under `captions/{id}/`, and `GET /library/source-url` only signs keys under `source/`. A caller cannot mint a presigned URL for an arbitrary object via these routes.
- **Deletes are prefix-scoped**: deleting a job removes only `captions/{job_id}/*` (via `repo.delete_prefix`), never another job's data or the source video.
- The generic `/files` browser still validates keys in `services/api/app/service/files.py::validate_key`; add bucket-prefix scoping there if you share a bucket with other workloads.

## No second credential

- Transcription/translation runs on-device (faster-whisper). There is **no external AI provider key** to manage or leak — B2 credentials are the only secret.

## Download Safety

- Presigned URLs force `Content-Disposition: attachment`
- Prevents inline rendering of user-uploaded content (XSS mitigation)

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
