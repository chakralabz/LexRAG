"""File type detection for parser routing.

This is the architecture-defined 2.2 layer. It classifies the uploaded file
family using byte sniffing first and extension cross-validation second so the
parser layer can make routing decisions without duplicating file-inspection
logic.
"""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.classification.document_family_classifier import (
    DocumentFamilyClassifier,
)
from lexrag.ingestion.file_ingestion.classification.extension_media_type_policy import (
    ExtensionMediaTypePolicy,
)
from lexrag.ingestion.file_ingestion.classification.text_sample_inspector import (
    TextSampleInspector,
)
from lexrag.ingestion.file_ingestion.magic_bytes_sniffer import MagicBytesSniffer
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)
from lexrag.ingestion.file_ingestion.schemas.file_type_detection import (
    FileTypeDetection,
)

HTML_MARKERS = (b"<html", b"<!doctype html", b"<body", b"<head")


class FileTypeDetector:
    """Classify files into document families used by parser selection."""

    def __init__(
        self,
        config: FileIngestionConfig | None = None,
        *,
        sniffer: MagicBytesSniffer | None = None,
    ) -> None:
        """Initialize the detector.

        Args:
            config: Optional ingestion configuration.
            sniffer: Optional byte sniffer override.
        """
        self.config = config or FileIngestionConfig()
        self.sniffer = sniffer or MagicBytesSniffer(config=self.config)
        self.family_classifier = DocumentFamilyClassifier(config=self.config)
        self.media_type_policy = ExtensionMediaTypePolicy(config=self.config)
        self.text_inspector = TextSampleInspector()

    def detect(self, path: Path) -> FileTypeDetection:
        """Detect the file family from content and extension.

        Args:
            path: File path to inspect.

        Returns:
            Structured file type detection result for parser routing.
        """
        sample = path.read_bytes()[: self.config.magic_byte_window]
        media_type, detection_method = self.sniffer.sniff(path)
        extension = path.suffix.lower()
        document_family = self.family_classifier.classify(
            extension=extension,
            media_type=media_type,
        )
        return FileTypeDetection(
            extension=extension,
            media_type=media_type,
            detection_method=detection_method,
            document_family=document_family,
            detected_type=document_family,
            has_pdf_header=sample.startswith(b"%PDF"),
            is_html=any(marker in sample.lower() for marker in HTML_MARKERS),
            is_text_like=self.text_inspector.is_likely_text(sample=sample),
            extension_matches_media_type=self.media_type_policy.matches(
                extension=extension,
                media_type=media_type,
            ),
            is_office_document=extension in self.config.office_extensions,
            is_email=extension in self.config.email_extensions
            or media_type == "message/rfc822",
        )
