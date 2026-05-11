"""Configuration schema for embedding generation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingGenerationConfig(BaseModel):
    """Operational settings for embedding generation."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str = Field(default="unversioned")
    batch_size: int = Field(default=32, ge=1)
    expected_dimension: int | None = Field(default=None, ge=1)
    max_retries: int = Field(default=3, ge=1)
    retry_base_seconds: float = Field(default=0.25, gt=0.0)
    max_sequence_tokens: int = Field(default=8192, ge=32)
