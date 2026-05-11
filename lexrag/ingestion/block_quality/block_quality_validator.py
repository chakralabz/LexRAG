"""Validation layer that filters malformed or low-value parsed blocks."""

from __future__ import annotations

import hashlib

from lexrag.ingestion.block_quality.schemas import (
    BlockQualityAssessment,
    BlockQualityConfig,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.observability.logging_runtime import get_logger
from lexrag.utils.text import TextNormalizer

logger = get_logger(__name__)


class BlockQualityValidator:
    """Apply the architecture's pre-chunk block quality rules.

    This validator deliberately favors deterministic heuristics over opaque
    statistical models so ingestion behavior is explainable and easy to tune.
    The output is still rich enough to support audits and downstream metrics.
    """

    def __init__(self, *, config: BlockQualityConfig | None = None) -> None:
        self.config = config or BlockQualityConfig()
        self.text_normalizer = TextNormalizer()
        self.last_assessments: list[BlockQualityAssessment] = []

    def validate(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Return blocks that satisfy the minimum ingestion quality bar.

        Args:
            blocks: Deduplicated parsed blocks in document order.

        Returns:
            Blocks that should continue into semantic planning. Kept blocks
            carry quality metadata for downstream audit and retrieval filtering.
        """
        return self._validate_blocks(blocks=blocks)

    def _validate_blocks(self, *, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        kept: list[ParsedBlock] = []
        dropped_hashes: set[str] = set()
        assessments: list[BlockQualityAssessment] = []
        for index, block in enumerate(blocks):
            next_block = blocks[index + 1] if index + 1 < len(blocks) else None
            assessment = self._assess_block(
                block=block,
                next_block=next_block,
                dropped_hashes=dropped_hashes,
            )
            assessments.append(assessment)
            if assessment.quality_status == "dropped":
                dropped_hashes.add(self._signature(block.text))
                continue
            kept.append(self._annotate_block(block=block, assessment=assessment))
        self.last_assessments = assessments
        logger.info(
            "Block quality finished: total_seen=%d total_kept=%d total_dropped=%d",
            len(blocks),
            len(kept),
            len(blocks) - len(kept),
        )
        return kept

    def _assess_block(
        self,
        *,
        block: ParsedBlock,
        next_block: ParsedBlock | None,
        dropped_hashes: set[str],
    ) -> BlockQualityAssessment:
        duplicate_drop = self._duplicate_drop_assessment(
            block=block, dropped_hashes=dropped_hashes
        )
        if duplicate_drop is not None:
            return duplicate_drop
        drop_reason = self._drop_reason(block=block)
        if drop_reason is not None:
            return BlockQualityAssessment(
                block_id=block.block_id,
                quality_status="dropped",
                quality_flags=[],
                drop_reason=drop_reason,
            )
        flags = self._flags(block=block, next_block=next_block)
        status = "flagged" if flags else "passed"
        return BlockQualityAssessment(
            block_id=block.block_id,
            quality_status=status,
            quality_flags=flags,
            drop_reason=None,
        )

    def _duplicate_drop_assessment(
        self,
        *,
        block: ParsedBlock,
        dropped_hashes: set[str],
    ) -> BlockQualityAssessment | None:
        if self._signature(block.text) not in dropped_hashes:
            return None
        return BlockQualityAssessment(
            block_id=block.block_id,
            quality_status="dropped",
            quality_flags=[],
            drop_reason="duplicate_dropped_block",
        )

    def _drop_reason(self, *, block: ParsedBlock) -> str | None:
        if not block.text.strip():
            return "empty_block"
        if self._is_micro_block(block=block):
            return "micro_block"
        if self._is_low_ocr_block(block=block):
            return "low_ocr_confidence"
        if self._is_junk_text(block=block):
            return "junk_text"
        if self._is_parser_anomaly(block=block):
            return "parser_anomaly"
        return None

    def _flags(
        self,
        *,
        block: ParsedBlock,
        next_block: ParsedBlock | None,
    ) -> list[str]:
        flags: list[str] = []
        if self._has_malformed_table_shape(block=block):
            flags.append("malformed_table")
        if self._is_truncated_block(block=block, next_block=next_block):
            flags.append("truncated_block")
        return flags

    def _annotate_block(
        self,
        *,
        block: ParsedBlock,
        assessment: BlockQualityAssessment,
    ) -> ParsedBlock:
        metadata = dict(block.metadata)
        metadata["quality_status"] = assessment.quality_status
        metadata["quality_flags"] = assessment.quality_flags
        metadata["drop_reason"] = assessment.drop_reason
        metadata["ocr_confidence"] = block.confidence if block.is_ocr else None
        return block.model_copy(update={"metadata": metadata})

    def _is_micro_block(self, *, block: ParsedBlock) -> bool:
        if block.block_type in {"heading", "table", "code"}:
            return False
        token_count = len(self.text_normalizer.tokenize_words(block.text))
        return token_count < self.config.min_tokens

    def _is_low_ocr_block(self, *, block: ParsedBlock) -> bool:
        confidence = block.confidence if block.is_ocr else None
        if confidence is None:
            return False
        return confidence < self.config.low_ocr_confidence_threshold

    def _is_junk_text(self, *, block: ParsedBlock) -> bool:
        text = block.text.strip()
        if "\ufffd" in text:
            return True
        symbol_chars = [
            char for char in text if not char.isalnum() and not char.isspace()
        ]
        if not text:
            return False
        return (
            len(symbol_chars) / len(text)
        ) >= self.config.junk_symbol_ratio_threshold

    def _is_parser_anomaly(self, *, block: ParsedBlock) -> bool:
        if block.block_type in {"table", "code", "code_block", "heading"}:
            return False
        text = block.text.strip()
        if len(text) < self.config.truncated_block_min_chars:
            return False
        alpha_chars = sum(char.isalpha() for char in text)
        digit_chars = sum(char.isdigit() for char in text)
        alpha_ratio = alpha_chars / len(text)
        digit_ratio = digit_chars / len(text)
        return (
            alpha_ratio < self.config.parser_alpha_ratio_threshold
            and digit_ratio < self.config.parser_digit_ratio_threshold
        )

    def _has_malformed_table_shape(self, *, block: ParsedBlock) -> bool:
        if block.block_type != "table":
            return False
        rows = [row for row in block.text.splitlines() if row.strip()]
        counts = {
            len([cell for cell in row.split("|") if cell.strip()]) for row in rows
        }
        return len(counts) > 1

    def _is_truncated_block(
        self,
        *,
        block: ParsedBlock,
        next_block: ParsedBlock | None,
    ) -> bool:
        text = block.text.rstrip()
        if len(text) < self.config.truncated_block_min_chars:
            return False
        if next_block is None or next_block.page <= block.page:
            return False
        if next_block.section != block.section:
            return False
        return text[-1].isalnum()

    def _signature(self, text: str) -> str:
        normalized = " ".join(self.text_normalizer.tokenize_non_whitespace(text))
        return hashlib.sha256(normalized.lower().encode("utf-8")).hexdigest()
