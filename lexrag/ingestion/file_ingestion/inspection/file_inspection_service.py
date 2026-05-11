"""Combine validation and type detection into one beginner-friendly service."""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.file_type_detector import FileTypeDetector
from lexrag.ingestion.file_ingestion.file_validation_service import (
    FileValidationService,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_report import (
    FileIngestionReport,
)


class FileInspectionService:
    """Produce the canonical inspection report for one or more files.

    This class is the conceptual center of the package. Callers that already
    have a safe resolved file path can use it directly without learning the
    loader/batching details.
    """

    def __init__(
        self,
        config: FileIngestionConfig | None = None,
        *,
        validator: FileValidationService | None = None,
        detector: FileTypeDetector | None = None,
    ) -> None:
        """Initialize the two inspection collaborators.

        Args:
            config: Optional shared ingestion configuration.
            validator: Optional validation service override for tests or custom wiring.
            detector: Optional type detector override for tests or custom wiring.
        """
        self.config = config or FileIngestionConfig()
        self.validator = validator or FileValidationService(config=self.config)
        self.detector = detector or FileTypeDetector(config=self.config)

    def inspect(self, path: Path) -> FileIngestionReport:
        """Inspect a single file and return validation plus type detection.

        Args:
            path: Resolved file path to inspect.

        Returns:
            Canonical inspection report that combines validation and detection.
        """
        # Validation and detection are both returned, even for blocked files, so
        # downstream logging and debugging keep the full pre-parse context.
        validation = self.validator.validate(path)
        detection = self.detector.detect(path)
        return FileIngestionReport(validation=validation, detection=detection)

    def inspect_batch(self, paths: list[Path]) -> list[FileIngestionReport]:
        """Inspect a batch while preserving order and duplicate detection.

        Args:
            paths: Resolved file paths to inspect together.

        Returns:
            Inspection reports in the same order as the input paths.
        """
        validations = self.validator.validate_many(paths)
        detections = [self.detector.detect(path) for path in paths]
        return [
            FileIngestionReport(validation=validation, detection=detection)
            for validation, detection in zip(validations, detections, strict=True)
        ]
