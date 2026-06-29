<!-- last_verified: 2026-06-29 -->
# Feature: Source Video Upload

## Purpose
Upload source videos from the browser to Backblaze B2 (under the `source/` prefix) with real-time progress, ready to subtitle from the Jobs page.

## Used By
- UI: `/upload` page, upload form component
- API: `POST /upload`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — orchestrates dropzone + progress + upload state
- `apps/web/src/components/upload/dropzone.tsx` — drag-and-drop via `react-dropzone` (video types, up to 2 GB)
- `apps/web/src/components/upload/upload-progress.tsx` — per-file progress bars
- `apps/web/src/lib/api-client.ts` — `uploadFile()` using XHR for progress events
- `services/api/app/runtime/upload.py` — HTTP handler, reads file chunks
- `services/api/app/service/upload.py` — validates video type/extension and orchestrates upload
- `services/api/app/repo/b2_client.py` — `upload_file()` via boto3 `put_object`

## Inputs
- file: `File` (from browser, multipart form data)
- content_type: string (from file MIME type) — must be a video type

## Outputs
- `FileUploadResponse`: key, filename, size, content_type, uploaded_at, url, basic metadata (checksums)
- Side effect: file stored in B2 under `source/{sanitized_filename}`

## Flow
- User drops or selects videos in the dropzone (MP4, MOV, MKV, WebM, AVI)
- Client validates size (max 2 GB) and type — rejected files show a toast with the reason
- XHR sends a multipart POST to `/upload` with progress events
- API rejects oversized requests early via `Content-Length`, validates the content type against the video allowlist, sanitizes the filename, validates the extension matches the MIME type, reads in 1 MB chunks with streaming size enforcement, and rejects empty files
- API writes to `source/{sanitized_filename}` via `put_object` and returns basic metadata (no image/PDF probing — that was trimmed for this app)

## Edge Cases
- File exceeds 2 GB → client-side rejection toast + API returns 413 if bypassed
- Non-video type → API returns 415
- Extension mismatches MIME type → API returns 415
- No filename / empty file → API returns 400
- Duplicate filename → B2 creates a new version (buckets are always versioned)
- B2 unreachable → API returns 500

## UX States
- Empty: dropzone with instructions
- Loading: per-file progress bars with spinner icon
- Error: red status icon, error message per file
- Complete: green checkmark, "Clear completed" button

## Verification
- Test files: `services/api/tests/test_upload_conflict.py`, `services/api/tests/test_error_handling.py`
- Required cases: source-prefix key, duplicate filename allowed, non-video rejection (415), empty file (400)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Local Transcription](transcription.md)
- [App Workflows](../app-workflows.md)
