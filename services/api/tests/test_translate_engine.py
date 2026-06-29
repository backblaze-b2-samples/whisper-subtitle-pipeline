"""Unit tests for the NLLB translation adapter.

No network, no model download: the CT2 translator + sentencepiece tokenizer
are faked so we exercise the FLORES mapping, the NLLB token protocol
(language prefix + EOS), timing preservation, and empty-segment pass-through
in isolation. The real model is covered by the end-to-end verify step.
"""

import pytest

from app.repo import translate_engine as te


class _FakeTokenizer:
    """Whitespace tokenizer standing in for sentencepiece."""

    def encode(self, text, out_type=str):
        return text.split()

    def decode(self, tokens):
        return " ".join(tokens)


class _FakeResult:
    def __init__(self, hypothesis):
        self.hypotheses = [hypothesis]


class _FakeTranslator:
    """Records inputs and echoes a deterministic 'translation'."""

    def __init__(self):
        self.calls = []

    def translate_batch(self, sources, *, target_prefix, **kwargs):
        self.calls.append({"sources": sources, "target_prefix": target_prefix})
        out = []
        for src_tokens, prefix in zip(sources, target_prefix, strict=True):
            # Mimic CT2: hypothesis starts with the target-language prefix
            # token and ends with EOS, with "translated" content between.
            content = [f"T:{t}" for t in src_tokens if t not in te._SPECIAL_TOKENS][1:]
            out.append(_FakeResult([prefix[0], *content, "</s>"]))
        return out


@pytest.fixture
def fake_model(monkeypatch):
    translator = _FakeTranslator()
    monkeypatch.setattr(te, "_load", lambda: (translator, _FakeTokenizer()))
    return translator


def test_flores_maps_curated_languages():
    assert te._flores("en") == "eng_Latn"
    assert te._flores("zh") == "zho_Hans"
    # Case / region-suffix tolerant.
    assert te._flores("PT-BR") == "por_Latn"


def test_flores_rejects_unknown_language():
    with pytest.raises(te.UnsupportedLanguageError):
        te._flores("xx")


def test_translate_preserves_timings_and_passes_empty_through(fake_model):
    segments = [
        {"start": 0.0, "end": 1.5, "text": "hello world"},
        {"start": 1.5, "end": 2.0, "text": "   "},  # whitespace-only
        {"start": 2.0, "end": 3.0, "text": "good"},
    ]
    out = te.translate_segments(segments, source_language="en", target_language="es")

    # Timings untouched, three segments out for three in.
    assert [(s["start"], s["end"]) for s in out] == [(0.0, 1.5), (1.5, 2.0), (2.0, 3.0)]
    # Empty segment passed through verbatim; non-empty got "translated".
    assert out[1]["text"] == "   "
    assert out[0]["text"] == "T:hello T:world"
    assert out[2]["text"] == "T:good"


def test_translate_builds_nllb_source_and_target_prefix(fake_model):
    te.translate_segments(
        [{"start": 0.0, "end": 1.0, "text": "hello world"}],
        source_language="en",
        target_language="fr",
    )
    call = fake_model.calls[0]
    # Source: [src_lang] + subwords + EOS.
    assert call["sources"][0] == ["eng_Latn", "hello", "world", "</s>"]
    # Target prefix forces the output language.
    assert call["target_prefix"] == [["fra_Latn"]]


def test_translate_skips_model_when_all_segments_empty(monkeypatch):
    def _boom():
        raise AssertionError("model must not load when there is nothing to translate")

    monkeypatch.setattr(te, "_load", _boom)
    out = te.translate_segments(
        [{"start": 0.0, "end": 1.0, "text": ""}],
        source_language="en",
        target_language="es",
    )
    assert out[0]["text"] == ""


def test_translate_rejects_unsupported_language(fake_model):
    with pytest.raises(te.UnsupportedLanguageError):
        te.translate_segments(
            [{"start": 0.0, "end": 1.0, "text": "hi"}],
            source_language="en",
            target_language="xx",
        )
