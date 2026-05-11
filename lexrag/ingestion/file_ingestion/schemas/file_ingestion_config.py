"""Top-level SDK config for file ingestion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .file_ingestion_antivirus_config import FileIngestionAntivirusConfig
from .file_ingestion_limits import FileIngestionLimits
from .file_ingestion_path_config import FileIngestionPathConfig
from .file_type_selection_config import FileTypeSelectionConfig
from .supported_file_type import SupportedFileType


class FileIngestionConfig(BaseModel):
    """Provide one SDK-facing config object for file ingestion.

    Callers can either instantiate the nested sections directly or use
    :meth:`from_options` for the common typed options path.
    """

    model_config = ConfigDict(frozen=True)

    file_types: FileTypeSelectionConfig = Field(
        default_factory=FileTypeSelectionConfig,
        description="Allowed file format configuration.",
    )
    limits: FileIngestionLimits = Field(
        default_factory=FileIngestionLimits,
        description="Size, page-count, and batching limits.",
    )
    path_policy: FileIngestionPathConfig = Field(
        default_factory=FileIngestionPathConfig,
        description="Filesystem resolution and safety policy.",
    )
    antivirus: FileIngestionAntivirusConfig = Field(
        default_factory=FileIngestionAntivirusConfig,
        description="Antivirus backend configuration.",
    )
    validation_messages: dict[str, str] = Field(
        default={
            "antivirus_infected": "The file was blocked by antivirus scanning.",
            "antivirus_error": "The antivirus scan could not be completed safely.",
            "corrupt_file": "The file appears malformed or truncated.",
            "duplicate_file_in_batch": "The same file content was uploaded twice in one batch.",
            "encrypted_pdf": "Encrypted PDFs must be decrypted before ingestion.",
            "extension_media_mismatch": "The file extension does not match the detected content type.",
            "file_empty": "The file is empty.",
            "file_too_large": "The file exceeds the configured size limit.",
            "file_too_many_pages": "The file exceeds the configured page limit.",
            "hash_unavailable": "The file could not be hashed safely.",
            "unsupported_extension": "The file extension is not supported.",
        },
        description="Stable user-facing messages for structured validation issues.",
    )

    @classmethod
    def from_options(
        cls,
        *,
        allowed_file_types: tuple[SupportedFileType, ...] | None = None,
        max_file_size_mb: int | None = None,
        max_page_count: int | None = None,
        max_batch_files: int = 1000,
        allowed_root_paths: tuple[str, ...] = (),
        follow_symlinks: bool = False,
        antivirus: FileIngestionAntivirusConfig | None = None,
    ) -> FileIngestionConfig:
        """Build a typed config from the most common caller options.

        Args:
            allowed_file_types: Optional allowed file-type enum list.
            max_file_size_mb: Optional maximum file size in megabytes.
            max_page_count: Optional maximum page count for paged formats.
            max_batch_files: Maximum number of files to expand from one path.
            allowed_root_paths: Optional allowed root directory boundaries.
            follow_symlinks: Whether symlink traversal is allowed.
            antivirus: Optional antivirus backend configuration.

        Returns:
            Fully materialized file ingestion config.
        """
        limits = FileIngestionLimits(
            max_file_size_bytes=(
                max_file_size_mb * 1024 * 1024
                if max_file_size_mb is not None
                else FileIngestionLimits().max_file_size_bytes
            ),
            max_page_count=(
                max_page_count
                if max_page_count is not None
                else FileIngestionLimits().max_page_count
            ),
            max_batch_files=max_batch_files,
        )
        return cls(
            file_types=FileTypeSelectionConfig(
                allowed_file_types=allowed_file_types or tuple(SupportedFileType)
            ),
            limits=limits,
            path_policy=FileIngestionPathConfig(
                allowed_root_paths=allowed_root_paths,
                follow_symlinks=follow_symlinks,
            ),
            antivirus=antivirus or FileIngestionAntivirusConfig(),
        )

    @property
    def allowed_extensions(self) -> tuple[str, ...]:
        """Return the allowed dotted extensions derived from file-type enums.

        Returns:
            Tuple of allowed dotted file extensions.
        """
        return tuple(file_type.extension for file_type in self.file_types.allowed_file_types)

    @property
    def office_extensions(self) -> tuple[str, ...]:
        """Return the configured OOXML office extensions.

        Returns:
            Tuple of dotted office document extensions.
        """
        return tuple(
            file_type.extension
            for file_type in self.file_types.allowed_file_types
            if file_type.is_office_document
        )

    @property
    def image_extensions(self) -> tuple[str, ...]:
        """Return the configured image extensions.

        Returns:
            Tuple of dotted image extensions.
        """
        return tuple(
            file_type.extension
            for file_type in self.file_types.allowed_file_types
            if file_type.is_image
        )

    @property
    def email_extensions(self) -> tuple[str, ...]:
        """Return the configured email container extensions.

        Returns:
            Tuple of dotted email extensions.
        """
        return tuple(
            file_type.extension
            for file_type in self.file_types.allowed_file_types
            if file_type.is_email
        )

    @property
    def min_file_size_bytes(self) -> int:
        """Return the configured minimum file size in bytes.

        Returns:
            Minimum file size in bytes.
        """
        return self.limits.min_file_size_bytes

    @property
    def max_file_size_bytes(self) -> int:
        """Return the configured maximum file size in bytes.

        Returns:
            Maximum file size in bytes.
        """
        return self.limits.max_file_size_bytes

    @property
    def max_page_count(self) -> int | None:
        """Return the configured maximum page count.

        Returns:
            Maximum allowed page count.
        """
        return self.limits.max_page_count

    @property
    def magic_byte_window(self) -> int:
        """Return the configured byte-sniffing window.

        Returns:
            Number of leading bytes to inspect.
        """
        return self.limits.magic_byte_window

    @property
    def max_batch_files(self) -> int:
        """Return the configured maximum batch expansion size.

        Returns:
            Maximum number of files a load request may expand to.
        """
        return self.limits.max_batch_files

    @property
    def follow_symlinks(self) -> bool:
        """Return whether symlink traversal is enabled.

        Returns:
            True when symlinks may be followed.
        """
        return self.path_policy.follow_symlinks

    @property
    def allowed_root_paths(self) -> tuple[str, ...]:
        """Return the configured allowed root boundaries.

        Returns:
            Tuple of allowed root path strings.
        """
        return self.path_policy.allowed_root_paths

    @property
    def clamav_socket_path(self) -> str | None:
        """Return the configured ClamAV socket path when applicable.

        Returns:
            ClamAV socket path when configured.
        """
        return self.antivirus.socket_path

    @property
    def clamav_host(self) -> str | None:
        """Return the configured ClamAV host when applicable.

        Returns:
            ClamAV host when configured.
        """
        return self.antivirus.host

    @property
    def clamav_port(self) -> int | None:
        """Return the configured ClamAV port when applicable.

        Returns:
            ClamAV port when configured.
        """
        return self.antivirus.port

    @property
    def block_on_missing_antivirus(self) -> bool | None:
        """Return the missing-scanner behavior override.

        Returns:
            Override controlling whether a missing scanner blocks ingestion.
        """
        return self.antivirus.block_on_missing_scanner

    @property
    def block_on_antivirus_error(self) -> bool:
        """Return whether scan-time antivirus errors should block ingestion.

        Returns:
            True when antivirus runtime errors are blocking.
        """
        return self.antivirus.block_on_scan_error

    @property
    def extension_media_type_map(self) -> dict[str, tuple[str, ...]]:
        """Return allowed MIME-like media types keyed by extension.

        Returns:
            Mapping from dotted extensions to allowed media types.
        """
        return {
            file_type.extension: file_type.media_types
            for file_type in self.file_types.allowed_file_types
        }
