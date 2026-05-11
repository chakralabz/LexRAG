"""ClamAV-backed antivirus scanner for production file ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.file_ingestion.antivirus.antivirus_scanner import (
    AntivirusScanner,
)
from lexrag.ingestion.file_ingestion.schemas.antivirus_scan_result import (
    AntivirusScanResult,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)


class ClamAVAntivirusScanner(AntivirusScanner):
    """Use the open-source ClamAV daemon when it is configured."""

    def __init__(self, config: FileIngestionConfig | None = None) -> None:
        """Store the antivirus configuration for future scans.

        Args:
            config: Optional shared ingestion configuration.
        """
        self.config = config or FileIngestionConfig()

    def scan(self, path: Path) -> AntivirusScanResult:
        """Scan a file with ClamAV and normalize the result.

        Args:
            path: File path to inspect.

        Returns:
            Normalized ClamAV scan result.
        """
        try:
            client = self._build_client()
            result = client.scan(str(path))
        except Exception as exc:
            return self._error_result(exc)
        if not result:
            return self._clean_result()
        signature_name = self._signature_name(result=result, path=path)
        return AntivirusScanResult(
            engine_name="clamav",
            status="infected",
            details=f"ClamAV reported malware in {path.name}.",
            signature_name=signature_name,
            blocking=True,
        )

    def _build_client(self) -> Any:
        """Create the configured ClamAV client transport.

        Returns:
            Configured `clamd` client instance.
        """
        clamd = self._load_clamd_module()
        if self.config.clamav_socket_path:
            return clamd.ClamdUnixSocket(path=self.config.clamav_socket_path)
        if self.config.clamav_host:
            return clamd.ClamdNetworkSocket(
                host=self.config.clamav_host,
                port=self.config.clamav_port or 3310,
            )
        return clamd.ClamdUnixSocket()

    def _load_clamd_module(self) -> Any:
        """Import the optional `clamd` client library lazily.

        Returns:
            Imported `clamd` module.
        """
        try:
            import clamd
        except Exception as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError("clamd client library is not installed") from exc
        return clamd

    def _signature_name(self, *, result: object, path: Path) -> str | None:
        """Extract the malware signature from the raw ClamAV response.

        Args:
            result: Raw result returned by the `clamd` client.
            path: File path that was scanned.

        Returns:
            Extracted malware signature when present.
        """
        if not isinstance(result, dict):
            return None
        entry = result.get(str(path))
        if not isinstance(entry, tuple) or len(entry) < 2:
            return None
        signature = entry[1]
        if isinstance(signature, str) and signature:
            return signature
        return None

    def _clean_result(self) -> AntivirusScanResult:
        """Build the canonical clean scan result.

        Returns:
            Structured scan result for a clean file.
        """
        return AntivirusScanResult(
            engine_name="clamav",
            status="clean",
            details="ClamAV scan completed without findings.",
            signature_name=None,
            blocking=False,
        )

    def _error_result(self, exc: Exception) -> AntivirusScanResult:
        """Fail closed or open according to configuration.

        Args:
            exc: Scan-time exception raised by the ClamAV client.

        Returns:
            Structured scan result for an antivirus execution error.
        """
        return AntivirusScanResult(
            engine_name="clamav",
            status="error",
            details=str(exc),
            signature_name=None,
            blocking=self.config.block_on_antivirus_error,
        )
