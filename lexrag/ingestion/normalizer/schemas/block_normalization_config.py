"""Typed configuration for the block-normalization layer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lexrag.config import Settings, get_settings


class BlockNormalizationConfig(BaseModel):
    """Immutable normalization settings shared by all block stages.

    Attributes:
        default_section_title: Fallback label used when a block lacks section
            context and the parser could not infer a stable heading.
        protected_block_types: Block types that should bypass destructive text
            cleanup because formatting or punctuation carries semantic meaning.
        legal_sensitive_document_types: Document categories that require more
            conservative cleanup policies.
        ocr_reject_threshold: OCR confidence below which the block is dropped.
        ocr_abstain_threshold: OCR confidence below which the block is kept but
            flagged as risky for downstream consumers.
        ocr_letter_collapse_threshold: Confidence threshold below which obvious
            letter-by-letter OCR splits are repaired.
        heading_max_words: Soft cap used to distinguish short headings from
            paragraph-like false positives.
        heading_sentence_like_char_limit: Character limit used together with
            sentence punctuation to demote likely false headings.
    """

    model_config = ConfigDict(frozen=True)

    default_section_title: str = Field(default="Untitled Section", min_length=1)
    protected_block_types: tuple[str, ...] = Field(
        default=("code", "code_block", "legal_citation", "table", "math_formula")
    )
    legal_sensitive_document_types: tuple[str, ...] = Field(
        default=("contract", "legislation", "regulation", "policy")
    )
    ocr_reject_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    ocr_abstain_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    ocr_letter_collapse_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    heading_max_words: int = Field(default=18, ge=1)
    heading_sentence_like_char_limit: int = Field(default=140, ge=20)

    @model_validator(mode="after")
    def validate_thresholds(self) -> BlockNormalizationConfig:
        """Ensures OCR policy thresholds define a valid decision ladder."""
        if self.ocr_reject_threshold > self.ocr_abstain_threshold:
            raise ValueError(
                "ocr_reject_threshold must be less than or equal to "
                "ocr_abstain_threshold"
            )
        return self


def build_block_normalization_config(
    settings: Settings | None = None,
) -> BlockNormalizationConfig:
    """Builds normalization config from process settings.

    Args:
        settings: Optional settings instance. When omitted, the process-wide
            cached settings object is used.

    Returns:
        A fully resolved immutable normalization config.
    """
    resolved_settings = settings or get_settings()
    return BlockNormalizationConfig(
        ocr_reject_threshold=resolved_settings.OCR_REJECT_THRESHOLD,
        ocr_abstain_threshold=resolved_settings.OCR_ABSTAIN_THRESHOLD,
    )
