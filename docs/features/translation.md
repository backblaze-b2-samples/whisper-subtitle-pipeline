<!-- last_verified: 2026-06-29 -->
# Feature: Translation

## Purpose
Emit a translated caption set alongside the source-language transcript, so a single video ships subtitles in more than one language.

## Deployment
`local` — runs **on-device**. Translation uses an NLLB-200 distilled (600M) model on the same CTranslate2 backend as transcription (CUDA → CPU autodetect, never GPU-required). No second API key; the CT2 weights + sentencepiece tokenizer download once from the public Hugging Face Hub.

> **Why not Whisper's own translate task?** faster-whisper's `task="translate"` can only ever translate speech **to English** — it ignores any other target language. Using it for non-English targets produced caption files labeled (e.g.) Spanish that actually contained the English/original text. Real multi-language subtitles therefore translate the *transcribed text* with a dedicated translation model.

## Used By
- UI: `/jobs` New Job / Edit form — task "Transcribe + Translate", "Translate to" selector
- API: `POST /jobs`, `POST /jobs/{id}/run`

## Core Functions
- `services/api/app/repo/translate_engine.py` — `translate_segments(segments, source_language, target_language)` (NLLB-200 on CTranslate2)
- `services/api/app/service/pipeline.py` — `run_job()` (the optional translate pass)

## Inputs
- `task`: `translate` (otherwise this feature is skipped)
- `target_language`: target language code (default `en`) — one of the curated `LANGUAGE_CHOICES`
- the source-language transcript segments (produced by the transcribe pass)

## Outputs
- a second caption set (SRT/VTT/JSON) written under `captions/<job_id>/` labeled with the target language, with the **same timings** as the source and the text translated into the target language
- the job's `languages` list includes both source and target

## Flow
1. The transcribe pass produces source-language segments and a detected source language.
2. If `task == "translate"`, the source language is known, and the target differs from it, the pipeline calls `translate_segments` to translate each segment's text source → target with NLLB-200. Segment timings are preserved; empty/silent segments pass through untouched.
3. The translated segments are rendered to SRT/VTT/JSON and written to B2 alongside the source set; the manifest records both languages.

## Language Mapping
Whisper emits ISO-639-1 codes (`en`, `es`, …); NLLB needs script-qualified FLORES-200 codes (`eng_Latn`, `spa_Latn`, …). The mapping for the curated UI languages lives in `translate_engine.py::_FLORES`. A language outside that set raises `UnsupportedLanguageError`.

## Edge Cases
- Target equals the detected source language → translate pass is skipped (no duplicate)
- `target_language == auto` (or empty) → skipped (you can't translate to "detect")
- Source language not detected → translate pass is skipped (no reliable source for NLLB)
- A segment with empty/whitespace text → passed through unchanged (NLLB would otherwise hallucinate text for silence)

## Verification
- Test files: `services/api/tests/test_translate_engine.py` (FLORES mapping + NLLB token protocol, mocked — no download), `services/api/tests/test_jobs.py` (job settings + lifecycle)
- Quick verify command: `pnpm test:api`
- Pass criteria: translate jobs produce a second labeled caption set whose text is actually in the target language (end-to-end against a real short video)

## Related Docs
- [Local Transcription](transcription.md)
- [Subtitle Export](subtitle-export.md)
