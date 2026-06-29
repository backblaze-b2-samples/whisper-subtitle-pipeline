import hashlib
import re
from datetime import UTC, datetime

from app.config import settings
from app.repo import upload_file
from app.types import FileMetadataDetail, FileUploadResponse
from app.types.formatting import humanize_bytes

# Source videos only — this app subtitles video libraries. faster-whisper
# decodes audio from these containers via its bundled PyAV (no system
# ffmpeg required).
ALLOWED_TYPES = {
    "video/mp4",
    "video/quicktime",  # .mov
    "video/x-matroska",  # .mkv
    "video/webm",
    "video/x-msvideo",  # .avi
}

MIME_EXTENSION_MAP: dict[str, set[str]] = {
    "video/mp4": {"mp4", "m4v"},
    "video/quicktime": {"mov", "qt"},
    "video/x-matroska": {"mkv"},
    "video/webm": {"webm"},
    "video/x-msvideo": {"avi"},
}

# Where source videos land in B2. Caption artifacts go under captions/.
SOURCE_PREFIX = "source/"

_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename: strip path components, remove unsafe chars, limit length."""
    name = filename.replace("\\", "/").split("/")[-1]
    name = name.replace("\x00", "")
    name = _SAFE_FILENAME_RE.sub("_", name)
    name = re.sub(r"[_.]{2,}", "_", name)
    name = name.lstrip(".").strip()
    if len(name) > 200:
        base, _, ext = name.rpartition(".")
        name = base[: 200 - len(ext) - 1] + "." + ext if ext else name[:200]
    return name or "unnamed"


def validate_extension_matches_type(filename: str, content_type: str) -> bool:
    """Verify the file extension is consistent with the declared MIME type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_exts = MIME_EXTENSION_MAP.get(content_type)
    if allowed_exts is None:
        return False
    if not ext:
        return True
    return ext in allowed_exts


def _basic_metadata(
    file_data: bytes, filename: str, content_type: str
) -> FileMetadataDetail:
    """Compute basic file metadata (no image/PDF/AV probing)."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=hashlib.md5(file_data, usedforsecurity=False).hexdigest(),
        sha256=hashlib.sha256(file_data).hexdigest(),
        uploaded_at=datetime.now(UTC),
    )


class UploadError(Exception):
    """Raised when upload validation fails."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def process_upload(
    file_data: bytes,
    filename: str,
    content_type: str,
    content_length: int | None = None,
) -> FileUploadResponse:
    """Validate and store a source video upload. Raises UploadError on failure."""
    if not filename:
        raise UploadError("No filename provided")

    if content_length and content_length > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    if content_type not in ALLOWED_TYPES:
        raise UploadError(
            f"Unsupported file type '{content_type}'. Upload a video "
            "(MP4, MOV, MKV, WebM, AVI).",
            status_code=415,
        )

    safe_name = sanitize_filename(filename)

    if not validate_extension_matches_type(safe_name, content_type):
        raise UploadError(
            "File extension does not match declared content type",
            status_code=415,
        )

    if len(file_data) == 0:
        raise UploadError("Empty file")

    if len(file_data) > settings.max_file_size:
        raise UploadError(
            f"File too large. Max size: {humanize_bytes(settings.max_file_size)}",
            status_code=413,
        )

    # B2 buckets are always versioned — uploading the same key creates a new
    # version automatically. No duplicate rejection needed.
    key = f"{SOURCE_PREFIX}{safe_name}"
    result = upload_file(file_data, key, content_type)
    metadata = _basic_metadata(file_data, safe_name, content_type)

    return FileUploadResponse(
        key=result.key,
        filename=result.filename,
        size_bytes=result.size_bytes,
        size_human=result.size_human,
        content_type=content_type,
        uploaded_at=result.uploaded_at,
        url=result.url,
        metadata=metadata,
    )
