"""Configuration schema for embedding text preparation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EmbeddingPreparationConfig(BaseModel):
    """Controls how canonical chunks are transformed into embedding text."""

    model_config = ConfigDict(frozen=True)

    max_embedding_tokens: int = Field(default=8192, ge=1)
    include_section_context: bool = Field(default=True)
    include_heading_context: bool = Field(default=True)
    table_row_limit: int = Field(default=32, ge=1)
    truncate_over_budget: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_row_limit(self) -> EmbeddingPreparationConfig:
        """Ensure table serialization remains within operational bounds."""
        if self.table_row_limit > 512:
            raise ValueError("table_row_limit must stay within operational bounds")
        return self
