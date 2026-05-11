"""Content-type sniffing helpers for upload classification.

The architecture prefers byte-level MIME detection rather than trusting file
extensions. This module first attempts `python-magic` when available and then
falls back to conservative signature-based heuristics.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from lexrag.ingestion.file_ingestion.classification.text_sample_inspector import (
    TextSampleInspector,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)

HTML_MARKERS = (b"<html", b"<!doctype html", b"<body", b"<head")
XML_MARKERS = (b"<?xml",)
EML_MARKERS = (b"from:", b"subject:", b"mime-version:", b"content-type:")


class MagicBytesSniffer:
    """Infer MIME-like media types from file bytes."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Initialize sniffer configuration.

        Args:
            config: Optional ingestion configuration.
        """
        self.config = config or FileIngestionConfig()
        self.text_inspector = TextSampleInspector()

    def sniff(self, path: Path) -> tuple[str, str]:
        """Return the best-effort media type and its detection source.

        Args:
            path: File path to inspect.

        Returns:
            A pair of `(media_type, detection_method)`.
        """
        sample = path.read_bytes()[: self.config.magic_byte_window]
        magic_result = self._sniff_with_python_magic(sample=sample)
        if magic_result is not None:
            return magic_result, "python-magic"
        return self._sniff_with_signatures(
            path=path,
            sample=sample,
            extension=path.suffix.lower(),
        )

    def _sniff_with_python_magic(self, *, sample: bytes) -> str | None:
        """Use libmagic when present because it is the highest-fidelity option.

        Args:
            sample: Leading byte sample from the file.

        Returns:
            Detected media type when `python-magic` succeeds.
        """
        try:
            import magic
        except Exception:
            return None
        try:
            detected = magic.from_buffer(sample, mime=True)
        except Exception:
            return None
        if not detected or detected == "application/octet-stream":
            return None
        return str(detected)

    def _sniff_with_signatures(
        self,
        *,
        path: Path,
        sample: bytes,
        extension: str,
    ) -> tuple[str, str]:
        """Apply conservative fallback signatures when libmagic is unavailable.

        Args:
            path: File path being inspected.
            sample: Leading byte sample from the file.
            extension: Lowercase filename extension.

        Returns:
            Pair of `(media_type, detection_method)`.
        """
        lowered = sample.lower()
        if sample.startswith(b"%PDF"):
            return "application/pdf", "signature"
        if sample.startswith(b"PK\x03\x04"):
            return self._sniff_zip_container(path=path, extension=extension)
        if sample.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png", "signature"
        if sample.startswith((b"\xff\xd8\xff",)):
            return "image/jpeg", "signature"
        if sample.startswith((b"II*\x00", b"MM\x00*")):
            return "image/tiff", "signature"
        if any(marker in lowered for marker in HTML_MARKERS):
            return "text/html", "heuristic"
        if any(marker in lowered for marker in XML_MARKERS):
            return "application/xml", "heuristic"
        if any(marker in lowered for marker in EML_MARKERS):
            return "message/rfc822", "heuristic"
        if self.text_inspector.is_likely_text(sample=sample):
            return "text/plain", "heuristic"
        return "application/octet-stream", "unknown"

    def _sniff_zip_container(self, *, path: Path, extension: str) -> tuple[str, str]:
        """Inspect ZIP-based containers to identify concrete OOXML document types.

        Args:
            path: File path being inspected.
            extension: Lowercase filename extension.

        Returns:
            Pair of `(media_type, detection_method)`.
        """
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile:
            return "application/zip", "signature"
        if "[Content_Types].xml" not in names:
            return "application/zip", "signature"
        if any(name.startswith("word/") for name in names):
            return self._docx_media_type(), "container"
        if any(name.startswith("xl/") for name in names):
            return self._xlsx_media_type(), "container"
        if any(name.startswith("ppt/") for name in names):
            return self._pptx_media_type(), "container"
        if extension in self.config.office_extensions:
            return self._office_media_type_for_extension(
                extension=extension
            ), "signature"
        return "application/zip", "signature"

    def _office_media_type_for_extension(self, *, extension: str) -> str:
        """Map configured OOXML extensions onto canonical media types.

        Args:
            extension: Lowercase filename extension.

        Returns:
            Canonical OOXML media type for the extension.
        """
        if extension == ".docx":
            return self._docx_media_type()
        if extension == ".xlsx":
            return self._xlsx_media_type()
        if extension == ".pptx":
            return self._pptx_media_type()
        return "application/zip"

    def _docx_media_type(self) -> str:
        """Return the canonical DOCX media type.

        Returns:
            Canonical DOCX media type string.
        """
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def _xlsx_media_type(self) -> str:
        """Return the canonical XLSX media type.

        Returns:
            Canonical XLSX media type string.
        """
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _pptx_media_type(self) -> str:
        """Return the canonical PPTX media type.

        Returns:
            Canonical PPTX media type string.
        """
        return (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
