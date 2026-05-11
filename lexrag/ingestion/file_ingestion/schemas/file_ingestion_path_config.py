"""SDK-facing path policy config for file ingestion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileIngestionPathConfig(BaseModel):
    """Control how the ingestion SDK resolves and constrains filesystem paths."""

    model_config = ConfigDict(frozen=True)

    follow_symlinks: bool = Field(
        default=False,
        description="Whether file loading may traverse symlinked paths.",
    )
    allowed_root_paths: tuple[str, ...] = Field(
        default=(),
        description="Optional absolute roots that loaded files must remain inside.",
    )
