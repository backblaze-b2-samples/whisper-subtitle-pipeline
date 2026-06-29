<!-- last_verified: 2026-06-29 -->
# Whisper Subtitle Pipeline

A self-hosted, open-source batch subtitling and translation service for video libraries — built on **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** and **[Backblaze B2](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-subtitle-pipeline)**. Upload raw videos to B2, transcribe them **on-device** (no per-minute SaaS fees, no second API key), and write **SRT + VTT subtitle files plus a transcript JSON** back to the same bucket. B2 is the single storage layer for both your source media and the 3–5× derived caption artifacts each video produces — a 10 TB library becomes 30–50 TB of captions across languages.

**Why this matters:** hosted transcription APIs bill per minute and keep your captions in their cloud. This app runs the same Whisper models locally and stores everything in one S3-compatible bucket you control. **B2 credentials only.**

**Audience:** video production teams, streaming platforms, and AI/dev teams that want an open, self-hosted alternative to hosted transcription APIs.

## Features

- **Local transcription** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2-accelerated Whisper) produces word/segment-timestamped transcripts entirely on-device. See [docs/features/transcription.md](docs/features/transcription.md).
- **Translation** — re-run through Whisper's translate task to emit a target language alongside the source. See [docs/features/translation.md](docs/features/translation.md).
- **SRT + VTT + JSON export** — derived caption artifacts written to `captions/<job_id>/` in B2. See [docs/features/subtitle-export.md](docs/features/subtitle-export.md).
- **Caption library + manifest** — a scoped `/library` view of source videos and their caption sets, backed by `captions/manifest.json`. See [docs/features/caption-library.md](docs/features/caption-library.md).
- **Subtitle pipeline dashboard** — videos processed, caption files generated, languages covered, the headline **derived/source storage ratio**, and total B2 usage. See [docs/features/dashboard.md](docs/features/dashboard.md).
- **Bucket explorer + upload** — full-bucket browse at `/files` and source-video upload at `/upload`, the reusable B2-backed scaffolding.

The primary entity is a **Subtitle Job** — one transcription(+translation) of a single source video, with full create / read / edit / delete / run lifecycle exposed in the UI.

## How it works

```
B2 source/<video>  --get_object-->  local temp file
        |
        v
  faster-whisper transcribe (+ optional translate)   [on-device: CUDA -> CPU]
        |
        v
  SRT / VTT / transcript JSON  --put_object-->  B2 captions/<job_id>/
        |
        v
  captions/manifest.json  (job/video index = system of record)
```

All B2 access is via the **S3-compatible API** through a single shared client with a custom user agent (`b2ai-whisper-subtitle-pipeline`). No b2-native API anywhere.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free **[Backblaze B2 account](https://www.backblaze.com/sign-up/ai-cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-subtitle-pipeline)**.

**1. Install dependencies**

```bash
pnpm install
```

**2. Set up the backend**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

> The first transcription downloads the Whisper model weights from Hugging Face (`base` is ~140 MB). Whisper models are **public — no token required**.

**3. Add your B2 credentials**

```bash
cp .env.example .env
```

Open `.env` and head to the [Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-whisper-subtitle-pipeline):

1. **Create a bucket.** Paste its unique name into `B2_BUCKET_NAME` and its region (e.g. `us-west-004`) into `B2_REGION`. The S3 endpoint is derived automatically as `https://s3.{B2_REGION}.backblazeb2.com`.
2. **Create an application key** with `Read and Write` permission:
   - **keyID** → `B2_APPLICATION_KEY_ID`
   - **applicationKey** → `B2_APPLICATION_KEY` *(only shown once)*

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Upload a video on the Upload page, then create a Subtitle Job on the Jobs page.

`pnpm dev` runs `pnpm doctor` first — a preflight that catches setup gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`, busy ports).

## Model & device selection

| Env var | Default | Notes |
|---------|---------|-------|
| `WHISPER_MODEL` | `base` | `tiny`/`base`/`small`/`medium`/`large-v3`. `base` (~140 MB) is a fast default; `large-v3` (~3 GB) is the production quality target. Selectable per-job in the New Job form. |
| `WHISPER_DEVICE` | `auto` | Auto-detect: **CUDA → CPU**. CTranslate2 has no Apple-MPS backend, so Apple Silicon correctly falls back to CPU. The app never hard-requires a GPU. |
| `WHISPER_COMPUTE_TYPE` | `auto` | `float16` on CUDA, `int8` on CPU. |
| `WHISPER_WORKER_THREADS` | `1` | Background worker / CPU threads. |

No system `ffmpeg` is required — faster-whisper decodes audio via bundled PyAV, and this app only emits *text* subtitles (it never burns captions into video).

## B2 storage layout

| Prefix | Contents |
|--------|----------|
| `source/<filename>` | Uploaded source videos |
| `captions/<job_id>/{lang}.srt` `.vtt` `.transcript.json` | Derived caption artifacts |
| `captions/manifest.json` | Job/video index — the system of record |

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui
- TanStack Query — caching, dedup, and live polling for running jobs
- Python 3.11+, FastAPI, boto3, Pydantic v2, **faster-whisper** (CTranslate2)
- Backblaze B2 (S3-compatible object storage)
- pnpm workspaces (monorepo)

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @whisper-subtitle-pipeline/web exec playwright install chromium` once first) |

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, pipeline data flow |
| [docs/features/](docs/features/) | Feature docs (transcription, translation, export, library, dashboard) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |
| [docs/exec-plans/](docs/exec-plans/) | Execution plans and tech debt tracker |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Built on the Vibe Coding Starter Kit

This app started from the [vibe-coding-starter-kit](https://github.com/backblaze-b2-samples/vibe-coding-starter-kit) — the B2-backed full-stack template (Next.js + FastAPI). The shared UI kit, bucket explorer, upload flow, and layered backend come from there; the subtitle pipeline is the app-specific layer on top.
