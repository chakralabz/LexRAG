"""Map low-level file signals onto parser-facing document families."""

from __future__ import annotations

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class DocumentFamilyClassifier:
    """Collapse MIME and extension data into stable parser routing families."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store the configuration used for family fallback decisions.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def classify(self, *, extension: str, media_type: str) -> str:
        """Return the parser-facing family for a detected file.

        Args:
            extension: Lowercase filename extension.
            media_type: Detected MIME-like media type.

        Returns:
            Parser-facing document family label.
        """
        if media_type == "application/pdf":
            return "pdf"
        if media_type.startswith("image/") or extension in self.config.image_extensions:
            return "image"
        if self._is_office_document(extension=extension, media_type=media_type):
            return "office"
        if media_type == "text/html":
            return "html"
        if media_type == "application/xml":
            return "xml"
        if media_type == "message/rfc822" or extension in self.config.email_extensions:
            return "email"
        if media_type.startswith("text/"):
            return "text"
        return extension.lstrip(".") or "unknown"

    def _is_office_document(self, *, extension: str, media_type: str) -> bool:
        """Recognize OOXML documents from either content or extension.

        Args:
            extension: Lowercase filename extension.
            media_type: Detected MIME-like media type.

        Returns:
            True when the file should be treated as an office document.
        """
        if media_type.startswith("application/vnd.openxmlformats-officedocument."):
            return True
        return extension in self.config.office_extensions
