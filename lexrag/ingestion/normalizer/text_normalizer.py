"""Generic text cleanup stage for non-protected blocks."""

from __future__ import annotations

import re
import unicodedata

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_CONTROL_CHARACTERS = {
    codepoint: None for codepoint in range(32) if chr(codepoint) not in {"\n", "\t"}
}
_MULTI_NEWLINES = re.compile(r"\n{3,}")
_MULTI_SPACES = re.compile(r"[ \t]{2,}")


class TextNormalizer(BaseNormalizer):
    """Normalizes generic text while respecting protected block semantics.

    This stage owns low-risk canonicalization such as Unicode normalization and
    whitespace cleanup. It deliberately bypasses block types where punctuation,
    layout, or syntax is itself part of the content contract.
    """

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Canonicalizes text for retrieval-safe indexing.

        Args:
            block: Parsed block candidate.

        Returns:
            Updated block with normalized plain text.
        """
        if self._should_bypass(block):
            return block
        normalized_text = self._normalize_text(block.text or "")
        return block.model_copy(update={"text": normalized_text})

    def should_drop(self, block: ParsedBlock) -> bool:
        """Drops empty or punctuation-only blocks after normalization."""
        if block.block_type == "heading":
            return False
        text = (block.text or "").strip()
        if not text:
            return True
        if len(text) < 3:
            return True
        return text in {"-", "--", "---"}

    def _should_bypass(self, block: ParsedBlock) -> bool:
        return block.block_type in self.config.protected_block_types

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = normalized.translate(_CONTROL_CHARACTERS)
        normalized = normalized.replace("\u200b", "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = _MULTI_NEWLINES.sub("\n\n", normalized)
        cleaned_lines = [self._clean_line(line) for line in normalized.splitlines()]
        semantic_lines = [line for line in cleaned_lines if line]
        return "\n".join(semantic_lines).strip()

    def _clean_line(self, line: str) -> str:
        return _MULTI_SPACES.sub(" ", line).strip()
