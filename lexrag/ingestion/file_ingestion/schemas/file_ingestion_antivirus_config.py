"""SDK-facing antivirus config for file ingestion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .antivirus_provider import AntivirusProvider


class FileIngestionAntivirusConfig(BaseModel):
    """Configure malware scanning behavior for the ingestion SDK."""

    model_config = ConfigDict(frozen=True)

    provider: AntivirusProvider = Field(
        default=AntivirusProvider.NONE,
        description="Antivirus backend used for file scanning.",
    )
    socket_path: str | None = Field(
        default=None,
        description="Optional UNIX socket path for a local ClamAV daemon.",
    )
    host: str | None = Field(
        default=None,
        description="Optional hostname for a network-accessible ClamAV daemon.",
    )
    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="Optional port for a network-accessible ClamAV daemon.",
    )
    block_on_missing_scanner: bool | None = Field(
        default=None,
        description="Override for whether a missing antivirus scanner blocks ingestion.",
    )
    block_on_scan_error: bool = Field(
        default=True,
        description="Whether antivirus runtime errors should block ingestion.",
    )

    @classmethod
    def clamav(
        cls,
        *,
        socket_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
        block_on_missing_scanner: bool | None = None,
        block_on_scan_error: bool = True,
    ) -> FileIngestionAntivirusConfig:
        """Build a ClamAV-backed antivirus config.

        Args:
            socket_path: Optional local ClamAV socket path.
            host: Optional remote ClamAV host.
            port: Optional remote ClamAV port.
            block_on_missing_scanner: Optional missing-scanner behavior override.
            block_on_scan_error: Whether antivirus runtime errors should block.

        Returns:
            Configured antivirus settings targeting ClamAV.
        """
        return cls(
            provider=AntivirusProvider.CLAMAV,
            socket_path=socket_path,
            host=host,
            port=port,
            block_on_missing_scanner=block_on_missing_scanner,
            block_on_scan_error=block_on_scan_error,
        )

    @model_validator(mode="after")
    def _validate_provider_settings(self) -> FileIngestionAntivirusConfig:
        """Ensure the configured antivirus backend has usable settings.

        Returns:
            Validated antivirus config.
        """
        if self.provider != AntivirusProvider.CLAMAV:
            return self
        if self.socket_path or self.host:
            return self
        raise ValueError(
            "ClamAV configuration requires either `socket_path` or `host`."
        )
