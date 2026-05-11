"""Section lineage stage for normalized blocks."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.normalizer.schemas import BlockNormalizationConfig
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_ANCHOR_SAFE_PATTERN = re.compile(r"[^a-z0-9]+")


class SectionPathNormalizer(BaseNormalizer):
    """Builds document section lineage required for citation-safe retrieval."""

    def __init__(self, config: BlockNormalizationConfig) -> None:
        super().__init__(config)
        self._section_stack: list[tuple[int, str]] = []

    def reset(self) -> None:
        """Clears heading lineage so state does not leak across documents."""
        self._section_stack = []

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Assigns stable section lineage and heading anchors.

        Args:
            block: Parsed block candidate.

        Returns:
            Updated block with section lineage embedded in metadata.
        """
        if block.block_type == "heading":
            return self._normalize_heading(block)
        return self._normalize_content_block(block)

    def _normalize_heading(self, block: ParsedBlock) -> ParsedBlock:
        level = block.heading_level or 1
        section_name = (
            block.section or block.text or self.config.default_section_title
        ).strip()
        self._pop_completed_sections(level)
        self._section_stack.append((level, section_name))
        parent_path = [name for _, name in self._section_stack[:-1]]
        section_path = [name for _, name in self._section_stack]
        return self._update_block(
            block=block,
            section_name=section_name,
            parent_path=parent_path,
            section_path=section_path,
        )

    def _normalize_content_block(self, block: ParsedBlock) -> ParsedBlock:
        active_path = [name for _, name in self._section_stack]
        resolved_section = (block.section or "").strip()
        if not resolved_section:
            resolved_section = (
                active_path[-1] if active_path else self.config.default_section_title
            )
        section_path = active_path or [resolved_section]
        return self._update_block(
            block=block,
            section_name=resolved_section,
            parent_path=active_path,
            section_path=section_path,
        )

    def _pop_completed_sections(self, level: int) -> None:
        while self._section_stack and self._section_stack[-1][0] >= level:
            self._section_stack.pop()

    def _update_block(
        self,
        *,
        block: ParsedBlock,
        section_name: str,
        parent_path: list[str],
        section_path: list[str],
    ) -> ParsedBlock:
        metadata = dict(block.metadata)
        metadata["section_path"] = section_path
        metadata["heading_anchor"] = self._build_heading_anchor(section_path)
        return block.model_copy(
            update={
                "section": section_name,
                "parent_section_path": parent_path,
                "metadata": metadata,
            }
        )

    def _build_heading_anchor(self, section_path: list[str]) -> str:
        joined = "-".join(part.strip().lower() for part in section_path if part.strip())
        compact = _ANCHOR_SAFE_PATTERN.sub("-", joined).strip("-")
        return compact or "untitled-section"
