<!-- last_verified: 2026-06-29 -->
# Reliability

Reliability expectations and practices for this project.

## Job durability & the restart caveat

- **System of record for completed jobs is `captions/manifest.json` in B2.** Every job state transition is written there, so finished jobs and their caption artifacts survive any restart.
- **In-flight (pending/running) job progress lives in an in-process registry.** Transcription runs on a single-worker background `ThreadPoolExecutor`; if the API process restarts mid-run, that in-flight job is lost (it won't auto-resume) and any partial artifacts already written remain in B2.
- **Recovery:** re-open the job and click **Run / Re-run** — it re-transcribes from the source video and overwrites the caption set. This is an accepted demo limitation; a production deployment would back the queue with a durable broker (e.g. Redis/RQ, Celery) and reconcile against the manifest on startup.

## Health Checks

- `GET /health` verifies B2 connectivity and returns `healthy` or `degraded`
- Health endpoint is always available, even when B2 is down

## Error Handling

- HTTP handlers return structured error responses with appropriate status codes
- External service failures (B2) are caught and surfaced as 500/503 responses
- No unhandled exceptions leak stack traces to clients

## Logging

- Structured JSON logging via Python stdlib
- Every request gets a `request_id` for tracing
- Log levels: ERROR for failures, WARNING for degraded state, INFO for requests

## Observability

- Request timing middleware logs duration for every request
- `/metrics` endpoint exposes basic Prometheus-format counters
- Upload success/failure counts tracked

## Graceful Degradation

- File listing returns empty list (not error) when B2 has no objects
- Metadata extraction failures don't block upload (return partial metadata)
- Frontend shows skeleton states while loading, error states on failure

## Deployment

- Railway health checks on `/health`
- Zero-downtime deploys via rolling updates
- Environment-specific configuration via env vars (no config files in prod)
