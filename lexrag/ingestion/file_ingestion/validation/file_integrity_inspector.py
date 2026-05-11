"""Low-cost structural checks used by the file validation layer."""

from __future__ import annotations

import zipfile
from pathlib import Path

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class FileIntegrityInspector:
    """Detect corruption and encryption without invoking full parsers."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store shared validation configuration.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def is_corrupted(self, *, path: Path, media_type: str) -> bool:
        """Return whether the file fails lightweight integrity checks.

        Args:
            path: File path to inspect.
            media_type: Detected MIME-like media type.

        Returns:
            True when the file appears corrupted or malformed.
        """
        extension = path.suffix.lower()
        if media_type == "application/pdf":
            return not path.read_bytes()[: self.config.magic_byte_window].startswith(
                b"%PDF"
            )
        if extension not in self.config.office_extensions:
            return False
        return self._is_corrupted_zip_archive(path=path)

    def is_encrypted_pdf(self, *, path: Path, media_type: str) -> bool:
        """Return whether a PDF appears to require a password.

        Args:
            path: File path to inspect.
            media_type: Detected MIME-like media type.

        Returns:
            True when the PDF appears encrypted.
        """
        if media_type != "application/pdf":
            return False
        header = path.read_bytes()[: self.config.magic_byte_window]
        if b"/Encrypt" in header:
            return True
        return self._is_encrypted_via_fitz(path=path)

    def _is_corrupted_zip_archive(self, *, path: Path) -> bool:
        """Validate OOXML ZIP containers using cheap archive checks.

        Args:
            path: File path to inspect.

        Returns:
            True when the archive looks malformed.
        """
        try:
            with zipfile.ZipFile(path) as archive:
                if "[Content_Types].xml" not in archive.namelist():
                    return True
                return archive.testzip() is not None
        except zipfile.BadZipFile:
            return True

    def _is_encrypted_via_fitz(self, *, path: Path) -> bool:
        """Use PyMuPDF when available because encrypted metadata is subtle.

        Args:
            path: File path to inspect.

        Returns:
            True when PyMuPDF reports that the file needs a password.
        """
        try:
            import fitz
        except Exception:
            return False
        try:
            with fitz.open(path) as document:  # pragma: no cover
                return bool(getattr(document, "needs_pass", False))
        except Exception:
            return False
