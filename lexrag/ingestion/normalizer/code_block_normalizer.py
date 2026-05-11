"""Normalization stage for code-like blocks."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_FENCE_PATTERN = re.compile(r"^\s*```(?P<language>[A-Za-z0-9_+-]+)?\s*$")
_TRAILING_SPACE_PATTERN = re.compile(r"[ \t]+$", re.MULTILINE)


class CodeBlockNormalizer(BaseNormalizer):
    """Preserves whitespace-sensitive formatting for code blocks.

    Code blocks are protected because indentation, line breaks, and fence
    markers carry meaning. This stage only performs line-ending cleanup and
    emits metadata helpful to retrieval and debugging.
    """

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Canonicalizes code blocks without changing executable structure.

        Args:
            block: Parsed block candidate.

        Returns:
            The block unchanged unless it represents code content.
        """
        if not self._is_code_block(block):
            return block
        text = self._normalize_line_endings(block.text or "")
        markdown = self._resolve_markdown(block=block, text=text)
        metadata = dict(block.metadata)
        metadata["code_language"] = self._extract_language(block.markdown)
        metadata["protected"] = True
        return block.model_copy(
            update={
                "block_type": "code_block",
                "text": text,
                "markdown": markdown,
                "metadata": metadata,
            }
        )

    def _is_code_block(self, block: ParsedBlock) -> bool:
        return block.block_type in {"code", "code_block"}

    def _normalize_line_endings(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = _TRAILING_SPACE_PATTERN.sub("", normalized)
        return normalized.strip("\n")

    def _resolve_markdown(self, *, block: ParsedBlock, text: str) -> str:
        markdown = block.markdown or text
        return self._normalize_line_endings(markdown)

    def _extract_language(self, markdown: str | None) -> str | None:
        if markdown is None:
            return None
        first_line = markdown.splitlines()[0] if markdown.splitlines() else ""
        match = _FENCE_PATTERN.match(first_line)
        if match is None:
            return None
        language = match.group("language")
        return language.lower() if language else None
