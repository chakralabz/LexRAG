"""Configuration schema for block quality validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BlockQualityConfig(BaseModel):
    """Thresholds shared by all block quality checks."""

    model_config = ConfigDict(frozen=True)

    min_tokens: int = Field(default=5, ge=1)
    low_ocr_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    junk_symbol_ratio_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    parser_alpha_ratio_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    parser_digit_ratio_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    truncated_block_min_chars: int = Field(default=40, ge=1)
