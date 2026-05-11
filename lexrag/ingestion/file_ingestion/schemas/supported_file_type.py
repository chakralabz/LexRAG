"""Typed file format options supported by the file ingestion SDK."""

from __future__ import annotations

from enum import StrEnum


class SupportedFileType(StrEnum):
    """Enumerate the concrete file formats supported by ingestion."""

    PDF = "pdf"
    HTML = "html"
    HTM = "htm"
    TEXT = "txt"
    MARKDOWN = "md"
    XML = "xml"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    TIF = "tif"
    TIFF = "tiff"
    EML = "eml"
    MSG = "msg"

    @classmethod
    def from_extension(cls, extension: str) -> SupportedFileType:
        """Build a file-type enum from a dotted or bare extension.

        Args:
            extension: Dotted or bare extension string such as ``.pdf`` or ``pdf``.

        Returns:
            Matching supported file-type enum.
        """
        normalized = extension.lower().lstrip(".")
        return cls(normalized)

    @property
    def extension(self) -> str:
        """Return the canonical dotted extension for the file type.

        Returns:
            Lowercase dotted extension such as ``.pdf``.
        """
        return f".{self.value}"

    @property
    def media_types(self) -> tuple[str, ...]:
        """Return allowed MIME-like media types for the file type.

        Returns:
            Tuple of MIME-like media types accepted for the file type.
        """
        media_types = {
            SupportedFileType.PDF: ("application/pdf",),
            SupportedFileType.HTML: ("text/html",),
            SupportedFileType.HTM: ("text/html",),
            SupportedFileType.TEXT: ("text/plain",),
            SupportedFileType.MARKDOWN: ("text/plain",),
            SupportedFileType.XML: ("application/xml", "text/plain"),
            SupportedFileType.DOCX: (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            SupportedFileType.XLSX: (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            SupportedFileType.PPTX: (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            SupportedFileType.PNG: ("image/png",),
            SupportedFileType.JPG: ("image/jpeg",),
            SupportedFileType.JPEG: ("image/jpeg",),
            SupportedFileType.TIF: ("image/tiff",),
            SupportedFileType.TIFF: ("image/tiff",),
            SupportedFileType.EML: ("message/rfc822", "text/plain"),
            SupportedFileType.MSG: ("application/octet-stream",),
        }
        return media_types[self]

    @property
    def is_office_document(self) -> bool:
        """Return whether the file type is an OOXML office document.

        Returns:
            True when the file type is DOCX, XLSX, or PPTX.
        """
        return self in {
            SupportedFileType.DOCX,
            SupportedFileType.XLSX,
            SupportedFileType.PPTX,
        }

    @property
    def is_image(self) -> bool:
        """Return whether the file type should be treated as an image.

        Returns:
            True when the file type is one of the supported image formats.
        """
        return self in {
            SupportedFileType.PNG,
            SupportedFileType.JPG,
            SupportedFileType.JPEG,
            SupportedFileType.TIF,
            SupportedFileType.TIFF,
        }

    @property
    def is_email(self) -> bool:
        """Return whether the file type is an email container.

        Returns:
            True when the file type is EML or MSG.
        """
        return self in {SupportedFileType.EML, SupportedFileType.MSG}
