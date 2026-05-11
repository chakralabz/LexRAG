"""Schema for runtime logging configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoggingConfig(BaseModel):
    """Typed logging configuration for process-wide setup.

    Attributes:
        level: Logging severity threshold accepted by the root logger.
        fmt: Output formatter mode. `text` targets humans, `json` targets
            production log shipping and search pipelines.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    level: str = Field(default="INFO", min_length=1)
    fmt: str = Field(default="text", min_length=1)
