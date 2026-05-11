"""Normalization stage for heading blocks and section labels."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_WHITESPACE_PATTERN = re.compile(r"\s+")


class HeadingNormalizer(BaseNormalizer):
    """Stabilizes heading blocks while avoiding false heading promotion.

    The parser is allowed to over-predict headings. This stage intentionally
    uses conservative demotion rules so we avoid destroying genuine section
    structure in legal and technical documents.
    """

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Normalizes heading labels and demotes clear paragraph false positives.

        Args:
            block: Parsed block candidate.

        Returns:
            Updated block with canonical heading metadata when appropriate.
        """
        if not self._is_heading_candidate(block):
            return block
        heading_text = self._resolve_heading_text(block)
        if self._should_demote(block=block, heading_text=heading_text):
            return self._demote_to_paragraph(block=block, heading_text=heading_text)
        return self._promote_heading(block=block, heading_text=heading_text)

    def _is_heading_candidate(self, block: ParsedBlock) -> bool:
        return (
            block.block_type in {"heading", "section"}
            or block.heading_level is not None
        )

    def _resolve_heading_text(self, block: ParsedBlock) -> str:
        raw_heading = block.text or block.section or self.config.default_section_title
        compact = _WHITESPACE_PATTERN.sub(" ", raw_heading).strip()
        return compact or self.config.default_section_title

    def _should_demote(self, *, block: ParsedBlock, heading_text: str) -> bool:
        if block.heading_level is not None:
            return False
        word_count = len(heading_text.split())
        if word_count > self.config.heading_max_words:
            return True
        long_sentence = len(heading_text) > self.config.heading_sentence_like_char_limit
        has_terminal_punctuation = heading_text.endswith((".", "!", "?"))
        return long_sentence and has_terminal_punctuation

    def _demote_to_paragraph(
        self, *, block: ParsedBlock, heading_text: str
    ) -> ParsedBlock:
        metadata = dict(block.metadata)
        metadata["heading_normalizer_demoted"] = True
        return block.model_copy(
            update={
                "block_type": "paragraph",
                "heading_level": None,
                "section": block.section or self.config.default_section_title,
                "text": heading_text,
                "metadata": metadata,
            }
        )

    def _promote_heading(self, *, block: ParsedBlock, heading_text: str) -> ParsedBlock:
        level = block.heading_level or 1
        return block.model_copy(
            update={
                "block_type": "heading",
                "heading_level": level,
                "section": heading_text,
                "text": heading_text,
            }
        )
