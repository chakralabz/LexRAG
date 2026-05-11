"""Conservative OCR repair and confidence policy stage."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_SOFT_HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
_HARD_LINE_BREAK = re.compile(r"(\w)\n(\w)")
_MULTI_SPACES = re.compile(r"[ \t]{2,}")
_SPACED_LETTERS = re.compile(r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b")


class OCRNormalizer(BaseNormalizer):
    """Repairs low-risk OCR artifacts and emits audit-friendly policy signals.

    The implementation is intentionally conservative. It repairs layout damage
    that is almost certainly wrong while protecting symbols such as ``§``,
    ``¶``, and em/en dashes that are often meaningful in legal documents.
    """

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Normalizes OCR text and attaches OCR risk metadata.

        Args:
            block: Parsed block candidate.

        Returns:
            Updated block with repaired text and OCR policy metadata.
        """
        if not block.is_ocr:
            return block
        text = self._repair_layout_breaks(block.text or "")
        text = self._repair_spaced_letters(text=text, confidence=block.confidence)
        metadata = dict(block.metadata)
        metadata["ocr_normalized"] = True
        metadata["ocr_quality_bucket"] = self._quality_bucket(block.confidence)
        metadata["ocr_policy_action"] = self._policy_action(block.confidence)
        metadata["ocr_reject_threshold"] = self.config.ocr_reject_threshold
        metadata["ocr_abstain_threshold"] = self.config.ocr_abstain_threshold
        return block.model_copy(update={"text": text.strip(), "metadata": metadata})

    def should_drop(self, block: ParsedBlock) -> bool:
        """Drops only OCR blocks that are below the hard reject threshold."""
        if not block.is_ocr or block.confidence is None:
            return False
        return block.confidence < self.config.ocr_reject_threshold

    def _repair_layout_breaks(self, text: str) -> str:
        repaired = _SOFT_HYPHEN_BREAK.sub(r"\1\2", text)
        repaired = _HARD_LINE_BREAK.sub(r"\1 \2", repaired)
        return _MULTI_SPACES.sub(" ", repaired)

    def _repair_spaced_letters(self, *, text: str, confidence: float | None) -> str:
        if (
            confidence is None
            or confidence >= self.config.ocr_letter_collapse_threshold
        ):
            return text
        return _SPACED_LETTERS.sub(self._collapse_spaced_letters, text)

    def _collapse_spaced_letters(self, match: re.Match[str]) -> str:
        return match.group(0).replace(" ", "")

    def _quality_bucket(self, confidence: float | None) -> str:
        if confidence is None:
            return "unknown"
        if confidence < self.config.ocr_abstain_threshold:
            return "low"
        if confidence < 0.75:
            return "medium"
        return "high"

    def _policy_action(self, confidence: float | None) -> str:
        if confidence is None:
            return "unknown"
        if confidence < self.config.ocr_reject_threshold:
            return "reject"
        if confidence < self.config.ocr_abstain_threshold:
            return "abstain"
        return "pass"
