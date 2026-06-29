# Build plan — `whisper-subtitle-pipeline`

Derived from a fresh clone of `vibe-coding-starter-kit` at
`.claude/scratch/vcsk-889752ed-9a9a-439e-b373-6f9040d324d1/` (the ONLY source of truth).
Builder must build at `./whisper-subtitle-pipeline`, strip git history, and obey
the parent standards in `../CLAUDE.md`.

---

## 1. Purpose

`whisper-subtitle-pipeline` is a self-hosted, OSS batch subtitling & translation
service for video libraries. A media/streaming team uploads raw videos
(MP4 / MKV / MOV) to Backblaze B2 under `source/`, and the app transcribes each
one **locally** with [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(CTranslate2-accelerated Whisper) — producing word-timestamped transcripts,
optionally translating them to a target language, and exporting **SRT + VTT
subtitle files plus a transcript JSON** to `captions/<job_id>/` in the *same*
bucket. A manifest index in B2 tracks every video and its caption set so players
and downstream pipelines can consume it. No per-minute SaaS fees, no second API
key — **B2 credentials only**. It demonstrates B2 as the single storage layer for
both source media and the 3–5× derived caption artifacts each video produces
(a 10 TB library → 30–50 TB of captions).

Audience: video production teams, streaming platforms, and AI/dev teams that want
an open, S3-compatible, self-hosted alternative to hosted transcription APIs.

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the **ceiling** — strip what this app doesn't need, keep the
reusable B2 scaffolding, add the subtitle pipeline on top of the same layered
backend and shadcn/ui frontend.

### KEEP (as-is — do not strip, rename, or replace)
- **UI kit / design system**: all of `apps/web/src/components/ui/`, the design
  tokens in `globals.css`, the `/design` reference page, and the
  `generating-loader` (reused for the "Transcribing…" running state).
- **Bucket explorer** — `/files` route + `apps/web/src/app/files/` +
  `components/files/` + its sidebar entry. **Non-negotiable keep**: full-bucket
  browse stays even though the app also adds a scoped Library view (see ADD).
- **Upload** — `/upload` route + `components/upload/`. Repurposed to upload
  **source videos** to the `source/` prefix, but the component + sidebar entry stay.
- **Settings** (`/settings`) and the sidebar nav shell (Dashboard, Upload, Files,
  Settings + Design System utility link). `settings-form.tsx` is the **form-UX
  exemplar** the new Job form must mirror (Select for finite fields, RadioGroup,
  `FormDescription` guidance, `defaultValues`).
- **Backend layering** (`types→config→repo→service→runtime`), the B2 `repo`
  adapter pattern, structured JSON logging, `/health`, `/metrics`, presigned-URL
  preview/download, single-source `.env`, TanStack Query data layer, structural
  tests, 300-line file cap.

### TRIM (remove from the starter)
- **Image/PDF metadata extraction** — `service/metadata.py`, the Pillow / PyPDF2
  deps in `requirements.txt`, `docs/features/metadata-extraction.md`, and any
  rich-metadata fields irrelevant to video. Keep only basic file metadata
  (filename / size / content-type via `mimetypes`). Verify removal doesn't break
  the upload path (simplify upload metadata to the basics). Update structural
  tests / `test_structure.py` layer-existence expectations if a layer empties.
- **Default dashboard widgets** — the generic stats-cards / upload-chart /
  recent-uploads content is illustrative; replace per §4 (the *components* stay
  as the styling exemplar but their data/labels change to subtitle-pipeline
  metrics). Adapt, don't delete the dashboard route.
- Starter-kit-specific README/AGENTS/ARCHITECTURE prose and the
  `docs/exec-plans/completed/*` history (replace with this app's docs; keep the
  exec-plans dir — this plan lands in `completed/initial-scaffold.md`).

### ADD (new for whisper-subtitle-pipeline)
- **Subtitle pipeline backend** (see §4): faster-whisper engine adapter in
  `repo/`, transcription/translation + subtitle-export orchestration in
  `service/`, a B2-manifest-backed job store, background worker, and new
  `runtime/` routers for jobs + library.
- **`/jobs`** route — the primary-entity (Subtitle Job) list + "New Job" create
  form, and **`/jobs/[id]`** detail (video player with live VTT caption track,
  transcript view, per-language SRT/VTT/JSON downloads, Re-run / Edit / Delete).
- **`/library`** route — **sample-specific asset explorer** scoped to this app's
  own prefixes: source videos under `source/` grouped with their derived caption
  sets under `captions/<job_id>/`. This is the mandated scoped explorer that
  complements (never replaces) the full bucket explorer at `/files`.
  > Note on the keep+add tension: `/files` (full bucket) and `/library` (scoped
  > to `source/` + `captions/`) coexist by design — `/files` is the generic B2
  > surface; `/library` is the subtitle-domain view. Both ship.
- Sidebar nav entries for **Jobs** and **Library**; `header.tsx` `pageTitles`
  entries for `/jobs`, `/jobs/[id]` (→ "Job"), and `/library`.

---

## 3. B2 surface (S3-compatible only)

All access via the S3-compatible API through the `repo/b2_client.py` adapter with
the custom user-agent. **No b2-native API anywhere.**

| Operation | S3 call | Used for |
|-----------|---------|----------|
| Upload source video | `put_object` | `/upload` → `source/<filename>` |
| Download source for transcription | `get_object` (stream to temp file) | faster-whisper reads a local file; new `repo` fn `download_to_path(key, dest)` |
| Write caption artifacts | `put_object` | `captions/<job_id>/{lang}.srt`, `.vtt`, `transcript.json` |
| Read/update manifest | `get_object` + `put_object` | `captions/manifest.json` (job/video index = system of record) |
| List library | `list_objects_v2` (prefix `source/`, `captions/`) | `/library`, dashboard metrics, manifest rebuild |
| Object metadata | `head_object` | detail/preview |
| Delete job artifacts | `delete_object` | DELETE job → remove `captions/<job_id>/*` (scoped to that job's prefix only) |
| Preview / download URLs | `generate_presigned_url` | `<video>` source + `<track>` VTT + SRT/JSON download links |

Custom user-agent set on the single shared S3 client via
`Config(user_agent_extra=...)` — value `b2ai-whisper-subtitle-pipeline` (see §6).
**No b2-native deviation.**

---

## 4. Key features

> **External API provider:** NONE. The transcription/translation engine is
> faster-whisper running **on-device** — `deployment: local` for every heavy
> feature. No second key; **B2 credentials only**. This matches the description's
> "Runs on local OSS — no second API key." The CPU-default / GPU-autodetect hard
> rule from `api-provider-selection.md` therefore applies to all of these.

**CPU-default / GPU-autodetect (hard rule, applies to every feature below):**
- `WHISPER_DEVICE` env, default `auto`. faster-whisper / CTranslate2 auto-detect:
  **CUDA → CPU**. `compute_type` auto-selects `float16` on CUDA, `int8` on CPU.
- **MPS deviation (record honestly):** CTranslate2 has **no Apple-MPS backend**,
  so on Apple Silicon the app correctly falls back to **CPU int8** — it never
  hard-requires a GPU. This is the "weak/no MPS support → CUDA→CPU fallback"
  case the rule explicitly allows.
- `WHISPER_MODEL` env, **default `base`** (fast, ~140 MB, good for a local demo /
  verify run). Document `large-v3` (the description's production target, ~3 GB) as
  the quality setting — selectable per-job in the create form. Model weights are
  fetched from Hugging Face on first use (Whisper models are **public — no token,
  unlike pyannote**). No system `ffmpeg` needed: faster-whisper decodes audio via
  bundled PyAV, and we only emit **text** SRT/VTT (never burn subtitles), so the
  Homebrew-ffmpeg/libass pitfall does not apply here.

Features (seed README list + `docs/features/<feature>.md` stubs):
1. **Local transcription** — faster-whisper produces word/segment-timestamped
   transcripts from `source/` videos. `deployment: local`. (`docs/features/transcription.md`)
2. **Translation** — re-run through Whisper's `task="translate"` to emit a target
   language alongside the source. `deployment: local`. (`docs/features/translation.md`)
3. **SRT + VTT + JSON export** — derived artifacts written to `captions/<job_id>/`
   in B2; demonstrates the 3–5× derived-data multiplier. (`docs/features/subtitle-export.md`)
4. **Caption library + manifest** — scoped `/library` view of source videos and
   their caption sets, backed by `captions/manifest.json`. (`docs/features/caption-library.md`)
5. **Subtitle pipeline dashboard** — videos processed, caption files generated,
   languages covered, **derived/source storage ratio** (the headline value prop),
   total B2 storage used. (rewritten `docs/features/dashboard.md`)

### Provider orchestration via Genblaze
NOT applicable — the description's stack is faster-whisper only; it does not
mention Genblaze / `genblaze-*`. Use faster-whisper directly, contained in `repo/`.

### Primary-entity lifecycle (mandatory UI completeness)
**Primary entity: `Subtitle Job`** — one transcription+translation request for a
single source video. ALL five lifecycle verbs are exposed in the UI (no omissions):

| Verb | UI surface | Backend |
|------|-----------|---------|
| **create** | `/jobs` → "New Job" form | `POST /jobs` (enqueues + auto-runs) |
| **read** | `/jobs/[id]` detail (player + transcript + downloads + status) | `GET /jobs`, `GET /jobs/{id}` |
| **edit** | "Edit" on detail → same form pre-filled (change target language / model / source language), then user re-runs | `PATCH /jobs/{id}` |
| **delete** | "Delete" on detail (AlertDialog confirm) — removes job + its `captions/<job_id>/` artifacts | `DELETE /jobs/{id}` |
| **run** | "Run / Re-run" button on detail | `POST /jobs/{id}/run` |

`omitted_ui_verbs`: **none** — all CRUD+run verbs are user-accessible and built.
Stay scoped to this one entity; do not add hypothetical features.

Job lifecycle states: `pending → running → succeeded | failed`. Long-running
transcription runs on a background worker (single-worker `ThreadPoolExecutor`);
`POST /jobs` returns immediately with a `pending` job, and the UI polls
`GET /jobs/{id}` via TanStack Query `refetchInterval` while `running`, showing the
kept `generating-loader`. System of record for completed jobs = `captions/manifest.json`
in B2; a small in-process registry tracks live progress. In-flight jobs lost on
restart is an acceptable demo limitation — document in `docs/RELIABILITY.md`.

### Form UX conventions (New Job create form + Edit form)
Mirror `settings-form.tsx` (react-hook-form + zod + shadcn `Form`).

(a) **Finite-value fields → selectors (both create & edit):**
- **Source video** → `Select` populated from the `source/` library (or the Upload
  page for a new file). Never free-text a key.
- **Source language** → `Select`: "Auto-detect" + a curated list (en, es, fr, de,
  pt, it, ja, zh, …).
- **Target language (translate to)** → `Select` from the same curated list.
- **Model size** → `Select`: `tiny | base | small | medium | large-v3`.
- **Task** → `RadioGroup`: "Transcribe only" | "Transcribe + Translate".

(b) **Create-form safe defaults as placeholder / `FormDescription` guidance only**
(never an autofill button): model **base**, source language **Auto-detect**,
target language **English**, task **Transcribe + Translate**. The edit form opens
pre-filled with the job's real values (no default-hints there).

---

## 5. Doc transforms

| Starter doc | Action |
|-------------|--------|
| `README.md` | **Rewrite** — subtitle-pipeline theme, feature list, quickstart with `WHISPER_MODEL` note + Standard-#3 `B2_*` env vars, the 30–50 TB derived-data value prop. Replace screenshots refs (real images added by a later pipeline step). |
| `AGENTS.md` | **Update** — repo map adds jobs/library; note faster-whisper engine is contained in `repo/`; keep the building-on-starter contract. |
| `ARCHITECTURE.md` | **Update** — add pipeline data flow: B2 `source/` → `get_object` → local faster-whisper transcribe(+translate) → SRT/VTT/JSON → `put_object` `captions/<job_id>/` → manifest update. |
| `docs/features/file-upload.md`, `file-browser.md` | **Keep / light edit** (source-video upload + bucket explorer). |
| `docs/features/dashboard.md` | **Rewrite** for subtitle-pipeline metrics. |
| `docs/features/metadata-extraction.md` | **Delete** (feature trimmed). |
| New: `docs/features/transcription.md`, `translation.md`, `subtitle-export.md`, `caption-library.md` | **Stub** per §4. |
| `docs/app-workflows.md`, `dev-workflows.md`, `SECURITY.md`, `RELIABILITY.md` | **Update** for the job pipeline (incl. restart caveat in RELIABILITY; presigned-URL / input-validation notes in SECURITY). |
| `docs/exec-plans/completed/initial-scaffold.md` | This plan moves here on PASS. |

---

## 6. Rename table (`vibe-coding-starter-kit` → `whisper-subtitle-pipeline`)

| Identifier | From | To |
|-----------|------|----|
| kebab slug / dir | `vibe-coding-starter-kit` | `whisper-subtitle-pipeline` |
| snake | `vibe_coding_starter_kit` | `whisper_subtitle_pipeline` |
| Title Case | `Vibe Coding Starter Kit` / `OSS Starter Kit` | `Whisper Subtitle Pipeline` |
| npm workspace scope | `@vibe-coding-starter-kit/web`, `/shared` | `@whisper-subtitle-pipeline/web`, `/shared` |
| Root `package.json` `name` | `vibe-coding-starter-kit` | `whisper-subtitle-pipeline` |
| FastAPI `title` (main.py) | `OSS Starter Kit API` | `Whisper Subtitle Pipeline API` |
| `APP_NAME` (lib/app-config.ts) | `OSS Starter Kit` | `Whisper Subtitle Pipeline` |
| `APP_DESCRIPTION` | `File management dashboard powered by Backblaze B2` | `Self-hosted batch video subtitling & translation, powered by faster-whisper and Backblaze B2` |
| user_agent_extra (b2_client.py) | `b2ai-oss-start` | `b2ai-whisper-subtitle-pipeline` |
| UTM `utm_content` (README + sidebar link) | `b2ai-oss-start` | `b2ai-whisper-subtitle-pipeline` |
| Railway / infra service name, any image tag / workflow slug | `vibe-coding-starter-kit` | `whisper-subtitle-pipeline` |
| e2e filter cmd in README/AGENTS | `@vibe-coding-starter-kit/web` | `@whisper-subtitle-pipeline/web` |

### Env-var rename — Standard #3 (parent CLAUDE.md), applied everywhere
The starter uses **old** names; new sample MUST use the standardized set. Update
`settings.py`, `main.py` (`REQUIRED_B2_SETTINGS` + `PLACEHOLDER_VALUES`),
`b2_client.py` (build endpoint from region), `.env.example`, README, and
`scripts/doctor.mjs` (+ any frontend reference):

| Old (starter) | New (Standard #3) |
|---------------|-------------------|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_ENDPOINT` | **`B2_REGION`** (e.g. `us-west-004`); derive endpoint `https://s3.{B2_REGION}.backblazeb2.com` in code |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` |

New non-B2 env (subtitle pipeline, documented in `.env.example`):
`WHISPER_MODEL` (default `base`), `WHISPER_DEVICE` (default `auto`),
`WHISPER_COMPUTE_TYPE` (default auto), optional `WHISPER_WORKER_THREADS` (default 1).

---

## 7. Dependency notes (pin ML deps — clean-install correctness)

- `requirements.txt`: **add** `faster-whisper>=1.1.0,<1.2` (pulls a compatible
  `ctranslate2`, `av`/PyAV, `tokenizers`, `onnxruntime`, `huggingface_hub`). Pin
  the window so a fresh clone reproduces — an unbounded ML dep is a false green
  (boots + tests pass, marquee feature breaks on clean install).
- **Remove** `Pillow`, `PyPDF2` (trimmed metadata). Keep `python-magic` only if
  upload still needs MIME sniffing; otherwise use stdlib `mimetypes`.
- End-to-end verify (later pipeline step) must actually run a transcription on a
  real short video — booting + unit tests alone won't catch a broken model load.

---

## 8. Verification expectations for the builder (before commit)
Run and confirm green: `pnpm lint`, `pnpm lint:api`, `pnpm test:api`,
`pnpm check:structure`, and `pnpm build` (catches unused imports / 404 routes /
unreachable UI — a timed-out build is known to skip frontend wiring). Confirm:
no b2-native calls; custom UA on the S3 client; all `B2_*` use Standard #3 names;
faster-whisper imported only in `repo/`; every Job lifecycle verb reachable in the
UI; New Job + Edit forms use selectors for finite fields with create-only default
hints; `/files` (bucket) AND `/library` (scoped) both present.
