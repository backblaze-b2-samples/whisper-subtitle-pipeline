"""Unit tests for source-video upload filename handling."""

from app.service import upload as upload_service
from app.types import FileMetadata


def _fake_upload(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "upload_file",
        lambda file_data, key, content_type: FileMetadata(
            key=key,
            filename=key.rsplit("/", 1)[-1],
            folder="source/",
            size_bytes=len(file_data),
            size_human="5 B",
            content_type=content_type,
            uploaded_at="2026-02-14T00:00:00Z",
            url=None,
        ),
    )


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    _fake_upload(monkeypatch)

    result = upload_service.process_upload(
        file_data=b"hello",
        filename="clip.mp4",
        content_type="video/mp4",
        content_length=5,
    )

    assert result.key == "source/clip.mp4"


def test_upload_targets_source_prefix(monkeypatch):
    """Source videos land under the source/ prefix, keeping their name."""
    _fake_upload(monkeypatch)

    result = upload_service.process_upload(
        file_data=b"hello",
        filename="My Movie.mov",
        content_type="video/quicktime",
        content_length=5,
    )

    assert result.key.startswith("source/")
    assert result.key == "source/My_Movie.mov"
