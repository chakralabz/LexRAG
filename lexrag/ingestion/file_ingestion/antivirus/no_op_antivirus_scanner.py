"""Default antivirus implementation used when no scanner is wired.

Production deployments can replace this class with a real scanner backed by
ClamAV, an internal malware gateway, or a SaaS provider. Keeping the default
behavior explicit avoids pretending that a scan happened when it did not.
"""

from __future__ import annotations

import os
from pathlib import Path

from lexrag.ingestion.file_ingestion.antivirus.antivirus_scanner import (
    AntivirusScanner,
)
from lexrag.ingestion.file_ingestion.schemas.antivirus_scan_result import (
    AntivirusScanResult,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class NoOpAntivirusScanner(AntivirusScanner):
    """Return a structured "skipped" scan result when no scanner is configured."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store configuration that determines fail-open versus fail-closed.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def scan(self, path: Path) -> AntivirusScanResult:
        """Return a non-blocking placeholder result.

        Args:
            path: File path to inspect.

        Returns:
            Scan result explaining that malware scanning was skipped.
        """
        blocking = self._is_production_env()
        return AntivirusScanResult(
            engine_name="noop",
            status="skipped",
            details=f"No antivirus scanner configured for {path.name}.",
            signature_name=None,
            blocking=blocking,
        )

    def _is_production_env(self) -> bool:
        """Fail closed in production when malware scanning is not configured.

        Returns:
            True when a missing antivirus scanner should block ingestion.
        """
        if self.config.block_on_missing_antivirus is not None:
            return self.config.block_on_missing_antivirus
        return os.getenv("LEXRAG_ENV", "DEV").upper() == "PROD"
