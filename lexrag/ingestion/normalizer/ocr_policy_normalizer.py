"""Compatibility wrapper for OCR policy-only consumers.

This class exists for call sites and tests that want OCR confidence decisions
without running the rest of the OCR repair logic. The main block-normalization
pipeline uses :class:`OCRNormalizer` directly.
"""

from __future__ import annotations

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.normalizer.schemas import (
    BlockNormalizationConfig,
    build_block_normalization_config,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class OCRPolicyNormalizer(BaseNormalizer):
    """Annotates OCR policy decisions using the shared normalization config."""

    def __init__(
        self,
        *,
        reject_threshold: float | None = None,
        abstain_threshold: float | None = None,
    ) -> None:
        base_config = build_block_normalization_config()
        config = BlockNormalizationConfig(
            ocr_reject_threshold=(
                reject_threshold
                if reject_threshold is not None
                else base_config.ocr_reject_threshold
            ),
            ocr_abstain_threshold=(
                abstain_threshold
                if abstain_threshold is not None
                else base_config.ocr_abstain_threshold
            ),
            default_section_title=base_config.default_section_title,
            protected_block_types=base_config.protected_block_types,
            legal_sensitive_document_types=base_config.legal_sensitive_document_types,
            ocr_letter_collapse_threshold=base_config.ocr_letter_collapse_threshold,
            heading_max_words=base_config.heading_max_words,
            heading_sentence_like_char_limit=(
                base_config.heading_sentence_like_char_limit
            ),
        )
        super().__init__(config)

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Adds OCR policy metadata without altering block text."""
        if not block.is_ocr:
            return block
        metadata = dict(block.metadata)
        metadata["ocr_reject_threshold"] = self.config.ocr_reject_threshold
        metadata["ocr_abstain_threshold"] = self.config.ocr_abstain_threshold
        metadata["ocr_policy_action"] = self._policy_action(block.confidence)
        return block.model_copy(update={"metadata": metadata})

    def should_drop(self, block: ParsedBlock) -> bool:
        """Drops OCR blocks below the configured hard reject threshold."""
        if not block.is_ocr or block.confidence is None:
            return False
        return block.confidence < self.config.ocr_reject_threshold

    def _policy_action(self, confidence: float | None) -> str:
        if confidence is None:
            return "unknown"
        if confidence < self.config.ocr_reject_threshold:
            return "reject"
        if confidence < self.config.ocr_abstain_threshold:
            return "abstain"
        return "pass"
