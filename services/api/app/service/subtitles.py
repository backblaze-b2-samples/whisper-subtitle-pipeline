"""Subtitle formatters — turn timestamped segments into SRT / VTT / JSON.

Pure functions, no I/O. The service layer writes the returned strings to B2.
We only ever emit *text* subtitles (never burn captions into the video), so
no system ffmpeg / libass is required.
"""

import json


def _format_timestamp(seconds: float, *, vtt: bool) -> str:
    """Format seconds as HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    if seconds < 0:
        seconds = 0.0
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    sep = "." if vtt else ","
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def to_srt(segments: list[dict]) -> str:
    """Render segments as SubRip (.srt)."""
    blocks = []
    for i, seg in enumerate(segments, start=1):
        start = _format_timestamp(seg["start"], vtt=False)
        end = _format_timestamp(seg["end"], vtt=False)
        blocks.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(blocks)


def to_vtt(segments: list[dict]) -> str:
    """Render segments as WebVTT (.vtt) — directly consumable by <track>."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp(seg["start"], vtt=True)
        end = _format_timestamp(seg["end"], vtt=True)
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def to_transcript_json(
    segments: list[dict], *, language: str, duration_seconds: float
) -> str:
    """Render a transcript JSON with segments + metadata."""
    payload = {
        "language": language,
        "duration_seconds": duration_seconds,
        "text": " ".join(seg["text"] for seg in segments).strip(),
        "segments": segments,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
