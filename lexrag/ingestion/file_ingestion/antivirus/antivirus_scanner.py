"""Contracts for optional antivirus integrations.

The architecture calls for a malware-scan hook before parsing. That hook
should be replaceable without forcing the rest of the ingestion stack to know
about vendor-specific APIs or response shapes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from lexrag.ingestion.file_ingestion.schemas.antivirus_scan_result import (
    AntivirusScanResult,
)


class AntivirusScanner(ABC):
    """Abstract malware scan interface used by file validation."""

    @abstractmethod
    def scan(self, path: Path) -> AntivirusScanResult:
        """Inspect a file and return a stable, structured scan result.

        Args:
            path: File path to inspect.

        Returns:
            Normalized malware scan result.
        """
