from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    # Standardized B2_* env names. The S3 endpoint is derived from the region
    # in repo/b2_client.py (https://s3.{region}.backblazeb2.com) — never
    # hardcode an endpoint here.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits — source videos are large, so allow up to 2 GB.
    max_file_size: int = 2 * 1024 * 1024 * 1024  # 2GB

    # Small durable counters (downloads, etc). Point at a persistent
    # volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- Subtitle pipeline (faster-whisper, runs on-device) ---
    # `auto` lets faster-whisper / CTranslate2 pick the best backend:
    # CUDA when available, otherwise CPU. CTranslate2 has no Apple-MPS
    # backend, so on Apple Silicon this correctly resolves to CPU int8 —
    # the app never hard-requires a GPU.
    whisper_model: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    whisper_worker_threads: int = 1

    # --- On-device translation (NLLB-200 via CTranslate2) ---
    # Whisper's `translate` task only ever targets English, so real
    # multi-language subtitles use a dedicated NLLB-200 distilled model on
    # the same CTranslate2 backend. The CT2 weights + sentencepiece tokenizer
    # download from this public HF repo on first translate (no token needed).
    # int8 keeps it CPU-friendly, matching the Whisper compute defaults.
    nllb_model_repo: str = "JustFrederik/nllb-200-distilled-600M-ct2-int8"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @property
    def b2_endpoint(self) -> str:
        """Derive the S3-compatible endpoint from the configured region."""
        return f"https://s3.{self.b2_region}.backblazeb2.com"


settings = Settings()
