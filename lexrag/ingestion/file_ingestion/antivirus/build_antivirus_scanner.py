"""Build the configured antivirus scanner for file ingestion."""

from __future__ import annotations

from lexrag.ingestion.file_ingestion.antivirus.antivirus_scanner import (
    AntivirusScanner,
)
from lexrag.ingestion.file_ingestion.antivirus.clamav_antivirus_scanner import (
    ClamAVAntivirusScanner,
)
from lexrag.ingestion.file_ingestion.antivirus.no_op_antivirus_scanner import (
    NoOpAntivirusScanner,
)
from lexrag.ingestion.file_ingestion.schemas.antivirus_provider import (
    AntivirusProvider,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


def build_antivirus_scanner(
    config: FileIngestionConfig | None = None,
) -> AntivirusScanner:
    """Return the best available antivirus scanner for the current config.

    Args:
        config: Optional shared ingestion configuration.

    Returns:
        Configured antivirus scanner implementation.
    """
    resolved = config or FileIngestionConfig()
    if resolved.antivirus.provider == AntivirusProvider.CLAMAV:
        return ClamAVAntivirusScanner(config=resolved)
    return NoOpAntivirusScanner(config=resolved)
