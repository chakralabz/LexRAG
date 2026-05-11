"""Configuration schema for block-level deduplication."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BlockDeduplicationConfig(BaseModel):
    """Thresholds and policy knobs for duplicate suppression.

    Attributes:
        near_duplicate_threshold: Jaccard threshold above which two blocks are
            considered near-duplicates.
        legal_sensitive_threshold: Confidence ceiling below which legal section
            content is preserved rather than suppressed.
        repeated_pattern_min_pages: Minimum distinct pages a top-of-page pattern
            must recur on before it is treated as boilerplate.
        header_footer_order_cutoff: Only early page positions are considered for
            repeated header/footer suppression in the absence of richer layout
            hints.
        boilerplate_unique_token_ratio: Maximum lexical uniqueness ratio for a
            recurring pattern to be treated as low-value boilerplate.
        legal_sensitive_document_types: Document families that require
            conservative duplicate handling.
        legal_sensitive_block_types: Block categories protected by the legal
            bypass rule.
    """

    model_config = ConfigDict(frozen=True)

    near_duplicate_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    legal_sensitive_threshold: float = Field(default=0.99, ge=0.0, le=1.0)
    repeated_pattern_min_pages: int = Field(default=4, ge=2)
    header_footer_order_cutoff: int = Field(default=1, ge=0)
    boilerplate_unique_token_ratio: float = Field(default=0.55, ge=0.0, le=1.0)
    legal_sensitive_document_types: tuple[str, ...] = Field(
        default=("contract", "legislation", "regulation", "policy")
    )
    legal_sensitive_block_types: tuple[str, ...] = Field(default=("clause", "section"))
