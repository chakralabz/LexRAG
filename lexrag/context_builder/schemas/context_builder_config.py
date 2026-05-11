"""Configuration schema for prompt context construction."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContextBuilderConfig(BaseModel):
    """Tune deduplication, compression, and conflict handling for context.

    Attributes:
        max_context_tokens: Hard ceiling for the formatted source window.
        near_duplicate_similarity_threshold: Ratio above which two chunks are
            considered textually redundant inside one context window.
        block_overlap_threshold: Ratio above which overlapping source blocks are
            considered equivalent evidence for prompt-budget purposes.
        conflict_value_count_threshold: Number of distinct structured values
            required before emitting a conflict warning.
        conflict_warning_sample_size: Number of example values surfaced in the
            prompt warning to keep it concise and readable.
    """

    model_config = ConfigDict(frozen=True)

    max_context_tokens: int = Field(default=3000, ge=128, le=32_000)
    near_duplicate_similarity_threshold: float = Field(default=0.98, ge=0.0, le=1.0)
    block_overlap_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    conflict_value_count_threshold: int = Field(default=2, ge=2, le=10)
    conflict_warning_sample_size: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def validate_thresholds(self) -> ContextBuilderConfig:
        """Keep the configuration semantically coherent."""

        if self.conflict_warning_sample_size > self.conflict_value_count_threshold + 5:
            raise ValueError("conflict_warning_sample_size is implausibly large")
        return self
