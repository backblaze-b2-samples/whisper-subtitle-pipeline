"""Unit tests for the subtitle formatters (pure, no I/O)."""

import json

from app.service.subtitles import to_srt, to_transcript_json, to_vtt

SEGMENTS = [
    {"start": 0.0, "end": 1.5, "text": "Hello world"},
    {"start": 1.5, "end": 3.25, "text": "Second line"},
]


def test_srt_format():
    srt = to_srt(SEGMENTS)
    assert "1\n00:00:00,000 --> 00:00:01,500\nHello world" in srt
    assert "2\n00:00:01,500 --> 00:00:03,250\nSecond line" in srt


def test_vtt_format():
    vtt = to_vtt(SEGMENTS)
    assert vtt.startswith("WEBVTT")
    # VTT uses a dot separator for milliseconds.
    assert "00:00:00.000 --> 00:00:01.500" in vtt
    assert "Hello world" in vtt


def test_transcript_json_format():
    raw = to_transcript_json(SEGMENTS, language="en", duration_seconds=3.25)
    data = json.loads(raw)
    assert data["language"] == "en"
    assert data["duration_seconds"] == 3.25
    assert data["text"] == "Hello world Second line"
    assert len(data["segments"]) == 2


def test_timestamp_clamps_negative():
    # Negative starts shouldn't produce a malformed timestamp.
    srt = to_srt([{"start": -1.0, "end": 0.5, "text": "x"}])
    assert "00:00:00,000 --> 00:00:00,500" in srt
