# Fix: translation produced original-language captions

## Problem
Translate jobs wrote a target-language caption set (e.g. `es.srt`) whose text
was actually the **source/original language**. Root cause: the pipeline used
faster-whisper's `task="translate"`, which can only ever translate speech **to
English** — it ignores `target_language`. For an English source, the "Spanish"
file was just the English transcript relabeled (the `en.srt` and `es.srt` were
byte-for-byte identical apart from labeling).

## Fix
Translate the **transcribed text** with a dedicated on-device model instead of
abusing Whisper's translate task.

- New repo adapter `app/repo/translate_engine.py`: NLLB-200 distilled (600M) on
  the same CTranslate2 backend faster-whisper already uses. `translate_segments`
  translates each segment's text source → target and preserves timings. Weights
  + sentencepiece tokenizer download from the public HF Hub on first use (no API
  key). FLORES-200 code mapping for the curated UI languages; empty segments
  pass through untouched.
- `app/service/pipeline.py`: the translate pass now runs `translate_segments`
  over the source transcript (only when the source language is known and differs
  from the target), instead of a second Whisper `task="translate"` call.
- `app/config/settings.py`: `nllb_model_repo` setting.
- `requirements.txt`: add `sentencepiece` (ctranslate2 + huggingface_hub already
  come via faster-whisper; no torch).

## Verification
- `pnpm lint:api`, `pnpm test:api`, `pnpm check:structure` — all green (83 tests).
- New unit test `tests/test_translate_engine.py` (FLORES mapping + NLLB token
  protocol, mocked — no download).
- End-to-end against a real English keynote with target `es`: `es.srt` now reads
  "si consigues trabajar en sólo uno de estos en tu carrera." (was the English
  source text before the fix). en → fr verified too.

## Frontend follow-up: player showed the source-language track

After the backend fix, the `/jobs/[id]` player still displayed source-language
subtitles. Cause (`apps/web/src/components/jobs/job-detail.tsx`): it used the
**first** VTT artifact (`artifacts.find(a => a.kind === "vtt")` → `en.vtt`) but
rendered the `<track>` with `srcLang={job.target_language}` — i.e. the source
track wearing the target label.

Fix: render one `<track>` per VTT language and default to the target language
(`defaultVttLang`); a small effect sets the matching `textTrack.mode` to
`showing` (a `<track>` added after the `<video>` mounts is not reliably shown
otherwise). The source track stays selectable in the player's caption menu.

Verified in the real browser with `apps/web/e2e/translated-captions.spec.ts`
(CI-safe: skips when no translate job exists). Confirmed the player defaults to
the target track and its cues differ from the source for en→es ("si consigues
trabajar en sólo uno de estos en tu carrera."), fr→en, and es→en.

## Notes / follow-ups
- Caption sets produced **before** this fix are still wrong; affected jobs must
  be **re-run** to regenerate correct translations.
- Whisper's `translate` task param is retained (signature guard) but unused by
  the pipeline.
