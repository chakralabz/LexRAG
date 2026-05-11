"""Schema for file type detection results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileTypeDetection(BaseModel):
    """Detected file classification used to choose parser routing."""

    model_config = ConfigDict(frozen=True)

    extension: str = Field(description="Normalized file extension.")
    media_type: str = Field(description="Best-effort MIME-like media type.")
    detection_method: str = Field(
        description="How the media type was determined, such as python-magic or signature."
    )
    document_family: str = Field(
        description="Parser-facing family such as pdf, html, office, image, or email."
    )
    detected_type: str = Field(
        description="Backward-compatible alias for the parser-facing document family."
    )
    has_pdf_header: bool = Field(
        description="Whether the leading bytes start with %PDF."
    )
    is_html: bool = Field(description="Whether HTML markers were found in the content.")
    is_text_like: bool = Field(
        description="Whether the bytes look UTF-safe and text-like."
    )
    extension_matches_media_type: bool = Field(
        description="Whether the extension is consistent with the detected content type."
    )
    is_office_document: bool = Field(
        description="Whether the file appears to be an Office Open XML document."
    )
    is_email: bool = Field(
        description="Whether the file appears to be an email container."
    )
