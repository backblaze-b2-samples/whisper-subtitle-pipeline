<!-- last_verified: 2026-06-29 -->
# Feature: Caption Library + Manifest

## Purpose
Provide a subtitle-domain view of the bucket: each source video grouped with the caption sets derived from it, backed by a manifest index. This complements — never replaces — the full-bucket explorer at `/files`.

## Used By
- UI: `/library` page
- API: `GET /library`, `GET /library/stats`, `GET /library/source-url`

## Core Functions
- `apps/web/src/components/library/library-view.tsx` — grouped cards
- `services/api/app/runtime/library.py` — library + stats routes
- `services/api/app/service/library.py` — `get_library()`, `get_pipeline_stats()`
- `services/api/app/service/jobs.py` — `captions/manifest.json` (system of record)

## Inputs
- None (loads automatically)

## Outputs
- `GET /library` → `LibraryEntry[]` — source video + its caption set, languages, sizes
- `GET /library/stats` → `PipelineStats`
- `GET /library/source-url?key=source/...` → presigned video URL

## Flow
1. The service lists objects under `source/` (videos) and joins the most recent job per source key from the manifest
2. Each entry exposes source size, derived caption size, languages, and a link to the job
3. The manifest (`captions/manifest.json`) is the durable index — it survives restarts; in-flight job progress lives in an in-process registry

## Scoping note
`/library` is scoped to this app's own prefixes (`source/` + `captions/`). The generic full-bucket browser at `/files` ships unchanged alongside it — both are intentional.

## Edge Cases
- No source videos → empty state
- A source video with no job yet → entry shows "No captions yet"
- Malformed manifest entry → skipped, logged (treated as empty rather than crashing)

## Verification
- Test files: `services/api/tests/test_jobs.py` (manifest store + CRUD)
- Quick verify command: `pnpm test:api`
- Pass criteria: library reflects sources joined with manifest jobs

## Related Docs
- [Subtitle Export](subtitle-export.md)
- [File Browser](file-browser.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
