<!-- last_verified: 2026-06-29 -->
# App Workflows

User journeys inside the application.

## Upload a Source Video

- User navigates to `/upload`
- Drops or selects videos (MP4, MOV, MKV, WebM, AVI) in the dropzone
- Client validates size (max 2 GB) and type
- Progress bar shows per-file upload status; on success the video lands under `source/` in B2
- See: [Source Video Upload](features/file-upload.md)

## Create & Run a Subtitle Job (primary flow)

- User navigates to `/jobs` and clicks **New Job**
- The form (mirroring the settings-form exemplar) uses selectors for every finite field:
  - **Source video** — `Select` populated from the `source/` library
  - **Source language** — `Select` (Auto-detect + curated list)
  - **Translate to** — `Select` (curated list)
  - **Model size** — `Select` (`tiny`/`base`/`small`/`medium`/`large-v3`)
  - **Task** — `RadioGroup` (Transcribe only / Transcribe + Translate)
  - Create-form safe defaults appear as `FormDescription` hints (never an autofill button): model **base**, source **Auto-detect**, target **English**, task **Transcribe + Translate**
- Submitting calls `POST /jobs`, which enqueues a `pending` job and auto-runs it, then routes to `/jobs/[id]`
- The detail page polls `GET /jobs/{id}` while `running`, showing the "Transcribing…" generating-loader
- On success: an embedded video player renders a VTT caption track per language, defaulting to the translated (target) track for translate jobs (the source track is still selectable in the player's caption menu); the transcript artifacts (SRT/VTT/JSON per language) are listed with download buttons
- See: [Local Transcription](features/transcription.md), [Translation](features/translation.md), [Subtitle Export](features/subtitle-export.md)

## Edit, Re-run, or Delete a Job

- On `/jobs/[id]`:
  - **Edit** opens the same form pre-filled with the job's real values (change target language / model / source language); saving calls `PATCH /jobs/{id}` (does not auto-run)
  - **Run / Re-run** calls `POST /jobs/{id}/run`
  - **Delete** opens an AlertDialog confirm; confirming calls `DELETE /jobs/{id}`, which removes the job and its `captions/<job_id>/` artifacts (scoped), then routes back to `/jobs`

## Browse the Caption Library

- User navigates to `/library`
- Each source video is shown as a card grouped with its caption set (languages, derived size, link to the job)
- Scoped to `source/` + `captions/`; for the full bucket, use `/files`
- See: [Caption Library](features/caption-library.md)

## Browse and Manage the Full Bucket

- User navigates to `/files`
- Tree view of every object; hover a row for preview / download / delete
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Stat cards show videos processed, caption files generated, languages covered, the **derived/source storage ratio**, and total B2 storage
- A storage breakdown bar contrasts source media vs derived captions; a recent-jobs table links into job details
- See: [Dashboard](features/dashboard.md)
