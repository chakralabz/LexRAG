"""Production-grade file ingestion boundary for pre-parse document checks.

This package implements the architecture-defined file ingestion layers:

1. File validation
2. File type detection

The package is intentionally independent from parsing so callers can validate
and classify uploads before any expensive parser dependency is invoked.

Internal layout:

- `antivirus/`: pluggable malware scanning implementations and factory
- `classification/`: shared MIME, extension, and family classification helpers
- `inspection/`: validation and type-detection orchestration
- `loading/`: batch expansion and load failure mapping helpers
- `validation/`: structured integrity and issue-building helpers
"""

from __future__ import annotations

from .antivirus import (
    ClamAVAntivirusScanner,
    NoOpAntivirusScanner,
    build_antivirus_scanner,
)
from .file_load_service import FileLoadService
from .file_path_resolver import FilePathResolver
from .file_type_detector import FileTypeDetector
from .file_validation_service import FileValidationService
from .inspection.file_inspection_service import FileInspectionService
from .schemas import (
    AntivirusProvider,
    AntivirusScanResult,
    FileIngestionAntivirusConfig,
    FileIngestionConfig,
    FileIngestionLimits,
    FileIngestionPathConfig,
    FileIngestionReport,
    FileLoadResult,
    FileTypeDetection,
    FileTypeSelectionConfig,
    FileValidationIssue,
    FileValidationResult,
    SupportedFileType,
)

__all__ = [
    "AntivirusProvider",
    "AntivirusScanResult",
    "ClamAVAntivirusScanner",
    "FileIngestionAntivirusConfig",
    "FileIngestionConfig",
    "FileIngestionLimits",
    "FileIngestionPathConfig",
    "FileIngestionReport",
    "FileInspectionService",
    "FileLoadResult",
    "FileLoadService",
    "FilePathResolver",
    "FileTypeDetection",
    "FileTypeDetector",
    "FileTypeSelectionConfig",
    "FileValidationIssue",
    "FileValidationResult",
    "FileValidationService",
    "NoOpAntivirusScanner",
    "SupportedFileType",
    "build_antivirus_scanner",
]
