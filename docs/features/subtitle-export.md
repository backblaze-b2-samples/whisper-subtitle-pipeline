<!-- last_verified: 2026-06-29 -->
# Feature: Subtitle Export (SRT + VTT + JSON)

## Purpose
Turn timestamped transcript segments into standard caption artifacts and write them back to Backblaze B2 — demonstrating the 3–5× derived-data multiplier each video produces.

## Used By
- UI: `/jobs/[id]` detail — VTT powers the live player track; SRT/VTT/JSON are downloadable
- API: `GET /jobs/{id}/artifacts/url` (presigned download links)
- Job: `service/pipeline.py` writes artifacts during a run

## Core Functions
- `services/api/app/service/subtitles.py` — `to_srt()`, `to_vtt()`, `to_transcript_json()` (pure formatters)
- `services/api/app/service/pipeline.py` — `_write_artifacts()` (puts each file to B2)
- `services/api/app/repo/b2_client.py` — `put_text()`

## Inputs
- `segments`: list of `{start, end, text}` from the engine
- `language`, `duration_seconds`

## Outputs
- `captions/<job_id>/{lang}.srt` — SubRip
- `captions/<job_id>/{lang}.vtt` — WebVTT (consumed directly by the player `<track>`)
- `captions/<job_id>/{lang}.transcript.json` — segments + full text + metadata
- These are the **derived artifacts** counted in the dashboard's derived/source ratio

## Flow
1. The pipeline renders SRT, VTT, and JSON from the segments
2. Each is uploaded to `captions/<job_id>/` with the right content type (`text/plain`, `text/vtt`, `application/json`)
3. `CaptionArtifact` records (kind, language, key, size) are stored on the job and in the manifest
4. Only **text** subtitles are emitted — captions are never burned into the video, so no system ffmpeg/libass is required

## Edge Cases
- Negative segment start → clamped to `00:00:00`
- Empty transcript → valid but empty SRT / `WEBVTT`-only VTT

## Verification
- Test files: `services/api/tests/test_subtitles.py`
- Required cases: SRT format, VTT format + header, JSON shape, negative-timestamp clamp
- Quick verify command: `pnpm test:api`
- Pass criteria: formatters produce spec-valid output

## Related Docs
- [Local Transcription](transcription.md)
- [Caption Library](caption-library.md)
