<!-- last_verified: 2026-06-29 -->
# Feature: Translation

## Purpose
Emit a translated caption set alongside the source-language transcript, so a single video ships subtitles in more than one language.

## Deployment
`local` — uses the same on-device faster-whisper model as transcription (CUDA → CPU autodetect, never GPU-required).

## Used By
- UI: `/jobs` New Job / Edit form — task "Transcribe + Translate", "Translate to" selector
- API: `POST /jobs`, `POST /jobs/{id}/run`

## Core Functions
- `services/api/app/repo/whisper_engine.py` — `transcribe(..., task="translate")`
- `services/api/app/service/pipeline.py` — `run_job()` (the optional translate pass)

## Inputs
- `task`: `translate` (otherwise this feature is skipped)
- `target_language`: target language code (default `en`)

## Outputs
- a second caption set (SRT/VTT/JSON) written under `captions/<job_id>/` labeled with the target language
- the job's `languages` list includes both source and target

## Flow
1. After the source-language transcription pass, if `task == "translate"` and the target differs from the detected language, the pipeline runs a second pass with `task="translate"`.
2. Whisper's translate task targets English; the resulting set is labeled with the requested target language so the player's `<track srcLang>` picks it up.
3. Both caption sets are written to B2 and recorded in the manifest.

## Edge Cases
- Target equals the detected source language → translate pass is skipped (no duplicate)
- `target_language == auto` → skipped (you can't translate to "detect")

## Verification
- Test files: `services/api/tests/test_jobs.py` (job settings + lifecycle)
- Quick verify command: `pnpm test:api`
- Pass criteria: translate jobs produce a second labeled caption set end-to-end

## Related Docs
- [Local Transcription](transcription.md)
- [Subtitle Export](subtitle-export.md)
