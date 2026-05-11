"""SDK-facing limit config for file ingestion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileIngestionLimits(BaseModel):
    """Control size, page-count, and batching limits for ingestion."""

    model_config = ConfigDict(frozen=True)

    min_file_size_bytes: int = Field(
        default=1,
        ge=0,
        description="Minimum accepted file size in bytes.",
    )
    max_file_size_bytes: int = Field(
        default=1_000_000_000,
        ge=1,
        description="Maximum accepted file size in bytes.",
    )
    max_page_count: int | None = Field(
        default=10_000,
        ge=1,
        description="Maximum page count for paged formats such as PDFs.",
    )
    magic_byte_window: int = Field(
        default=4096,
        ge=64,
        description="Leading byte window used for MIME sniffing and header checks.",
    )
    max_batch_files: int = Field(
        default=1000,
        ge=1,
        description="Maximum number of concrete files a single load request may expand to.",
    )
