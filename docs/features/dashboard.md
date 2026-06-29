<!-- last_verified: 2026-06-29 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the subtitle pipeline — how much media has been processed and the headline derived-data multiplier, all stored on Backblaze B2.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /library/stats`, `GET /jobs`

## Core Functions
- `apps/web/src/components/dashboard/pipeline-stats-cards.tsx` — 5 stat cards
- `apps/web/src/components/dashboard/storage-breakdown.tsx` — source vs derived bar
- `apps/web/src/components/dashboard/recent-jobs-table.tsx` — last 8 jobs
- `apps/web/src/lib/api-client.ts` — `getPipelineStats()`, `getJobs()`
- `services/api/app/runtime/library.py` — `GET /library/stats` handler
- `services/api/app/service/library.py` — `get_pipeline_stats()` business logic
- `services/api/app/repo/b2_client.py` — `list_files()` data access

## Canonical Files
- Dashboard stats: `apps/web/src/components/dashboard/pipeline-stats-cards.tsx`
- Stats service logic: `services/api/app/service/library.py`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /library/stats` → `PipelineStats` (videos_processed, caption_files, languages_covered, source/captions size, **derived_ratio**, total_b2_size)
- `GET /jobs` → `Job[]` for the recent-jobs table (sorted newest-first)

## Flow
- Page loads → parallel calls for pipeline stats + job list
- Stat cards show videos processed, caption files generated, languages covered, **derived/source storage ratio** (the value prop), and total B2 storage
- Storage breakdown bar shows source media vs derived caption bytes
- Recent-jobs table shows the last 8 jobs with status; clicking a row opens the job detail

## Edge Cases
- API unavailable → inline `ErrorState` with retry (cards never lie with fake zeros)
- No videos/jobs yet → empty states; ratio shows `0×`
- Large bucket → stats paginate through all objects under `source/` and `captions/`

## UX States
- Loading: skeletons for cards, breakdown, and table
- Empty: "No jobs yet" with prompt to create one
- Loaded: populated cards, breakdown, table

## Verification
- Test files: `services/api/tests/test_jobs.py` (the library service consumes the same job store)
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure && pnpm build`
- Pass criteria: all pytest tests green, no ruff/eslint violations, build succeeds

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Caption Library](caption-library.md)
- [App Workflows](../app-workflows.md)
