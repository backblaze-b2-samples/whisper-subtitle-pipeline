from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    """Basic file metadata for a source video.

    The starter kit shipped rich image/PDF metadata extraction (Pillow,
    PyPDF2); this app trims that — videos only need filename / size /
    content-type plus content checksums.
    """

    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
