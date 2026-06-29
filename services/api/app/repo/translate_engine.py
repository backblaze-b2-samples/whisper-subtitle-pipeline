"""On-device text translation via NLLB-200 on CTranslate2.

The second ML adapter in the repo layer. Speech recognition lives in
`whisper_engine.py`; storage stays on boto3 in `b2_client.py`. This module
owns *translation*.

Why a separate model: faster-whisper's `task="translate"` can only ever
translate speech **to English** — it ignores any other target language. To
produce subtitles in the languages the UI actually offers, we translate the
already-transcribed text with NLLB-200 distilled (600M), running on the same
CTranslate2 backend faster-whisper uses. It stays **on-device** (no second
API key); the CT2 weights + sentencepiece tokenizer download from the public
Hugging Face Hub on first use, exactly like the Whisper weights.
"""

import functools
import logging

from app.config import settings
from app.repo.whisper_engine import _resolve_compute_type, _resolve_device

logger = logging.getLogger(__name__)

# Whisper / ISO-639-1 codes -> NLLB FLORES-200 codes, for the curated UI
# language set (see app/types/jobs.py::LANGUAGE_CHOICES). NLLB needs the
# script-qualified code; Whisper emits the bare two-letter code.
_FLORES: dict[str, str] = {
    "en": "eng_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "pt": "por_Latn",
    "it": "ita_Latn",
    "nl": "nld_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "zh": "zho_Hans",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",
    "hi": "hin_Deva",
}

# Tokens NLLB emits around the real content — stripped before decoding.
_SPECIAL_TOKENS = frozenset({"</s>", "<s>", "<pad>", "<unk>"})


class UnsupportedLanguageError(ValueError):
    """A source/target language has no NLLB FLORES-200 mapping."""


def _flores(code: str) -> str:
    """Map a Whisper/ISO-639-1 code to an NLLB FLORES-200 code."""
    norm = (code or "").split("-")[0].lower()
    if norm not in _FLORES:
        raise UnsupportedLanguageError(
            f"Translation not supported for language '{code}'"
        )
    return _FLORES[norm]


@functools.lru_cache(maxsize=1)
def _load():
    """Download (first use) + load the NLLB CT2 model and its tokenizer.

    Cached for the process lifetime — the model is large, so we load once.
    """
    import ctranslate2
    import sentencepiece as spm
    from huggingface_hub import snapshot_download

    repo = settings.nllb_model_repo
    logger.info("Loading NLLB translation model from %s", repo)
    model_dir = snapshot_download(repo)
    device = _resolve_device()
    translator = ctranslate2.Translator(
        model_dir,
        device=device,
        compute_type=_resolve_compute_type(device),
        inter_threads=1,
        intra_threads=max(1, settings.whisper_worker_threads),
    )
    tokenizer = spm.SentencePieceProcessor()
    tokenizer.load(f"{model_dir}/sentencepiece.bpe.model")
    return translator, tokenizer


def translate_segments(
    segments: list[dict], *, source_language: str, target_language: str
) -> list[dict]:
    """Translate each segment's text, preserving its start/end timings.

    `segments` are `{start, end, text}` dicts (the whisper_engine shape).
    Returns the same shape with `text` translated source -> target. Empty
    segments pass through untouched (NLLB would otherwise hallucinate text
    for silence).
    """
    src = _flores(source_language)
    tgt = _flores(target_language)

    # Only translate segments that actually have text; keep empties in place.
    indexed = [(i, s) for i, s in enumerate(segments) if s["text"].strip()]
    out = [dict(s) for s in segments]
    if not indexed:
        return out

    translator, tokenizer = _load()
    sources = [
        [src, *tokenizer.encode(s["text"], out_type=str), "</s>"]
        for _, s in indexed
    ]
    results = translator.translate_batch(
        sources,
        target_prefix=[[tgt]] * len(sources),
        beam_size=2,
        max_batch_size=16,
    )
    for (i, _), res in zip(indexed, results, strict=True):
        tokens = res.hypotheses[0]
        # translate_batch echoes the target-language prefix token first.
        if tokens and tokens[0] == tgt:
            tokens = tokens[1:]
        tokens = [t for t in tokens if t not in _SPECIAL_TOKENS]
        out[i]["text"] = tokenizer.decode(tokens).strip()
    return out
