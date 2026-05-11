"""Shared extension and media-type policy used across ingestion stages."""

from __future__ import annotations

from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class ExtensionMediaTypePolicy:
    """Encapsulate allowlist and extension-to-media validation rules."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store the immutable ingestion policy configuration.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def is_allowed_extension(self, extension: str) -> bool:
        """Return whether the extension is allowlisted for ingestion.

        Args:
            extension: Lowercase filename extension.

        Returns:
            True when the extension is allowed for ingestion.
        """
        return extension in self.config.allowed_extensions

    def matches(self, *, extension: str, media_type: str) -> bool:
        """Return whether a detected media type is valid for an extension.

        Args:
            extension: Lowercase filename extension.
            media_type: Detected MIME-like media type.

        Returns:
            True when the media type is allowed for the extension.
        """
        allowed_media_types = self.config.extension_media_type_map.get(extension)
        if allowed_media_types is None:
            return False
        return media_type in allowed_media_types
