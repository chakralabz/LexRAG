"""Final metadata enrichment stage for normalized blocks."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.normalizer.schemas import BlockNormalizationConfig
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_ANCHOR_SAFE_PATTERN = re.compile(r"[^a-z0-9]+")


class MetadataEnricher(BaseNormalizer):
    """Attaches consistent audit metadata required by downstream layers.

    This stage is intentionally last so it can summarize the final normalized
    state instead of leaking transitional metadata from partially cleaned blocks.
    """

    def __init__(self, config: BlockNormalizationConfig) -> None:
        super().__init__(config)
        self._block_index = 0

    def reset(self) -> None:
        """Resets the per-document block counter."""
        self._block_index = 0

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Emits stable retrieval-safe metadata for the normalized block.

        Args:
            block: Fully normalized block.

        Returns:
            Block with enriched metadata used by chunking, indexing, and audit.
        """
        metadata = dict(block.metadata)
        section_path = self._resolve_section_path(block=block, metadata=metadata)
        metadata["normalized"] = True
        metadata["normalizer"] = "block_normalizer"
        metadata["page_number"] = block.page
        metadata["document_section"] = block.section
        metadata["block_type"] = block.block_type
        metadata["block_index"] = self._block_index
        metadata["section_path"] = section_path
        metadata["heading_anchor"] = self._build_heading_anchor(section_path)
        metadata["ocr_confidence"] = block.confidence if block.is_ocr else None
        metadata["protected"] = self._is_protected(block)
        self._block_index += 1
        return block.model_copy(update={"metadata": metadata})

    def _resolve_section_path(
        self, *, block: ParsedBlock, metadata: dict[str, object]
    ) -> list[str]:
        raw_path = metadata.get("section_path")
        if isinstance(raw_path, list) and all(
            isinstance(item, str) for item in raw_path
        ):
            return raw_path
        if block.parent_section_path:
            return [*block.parent_section_path, block.section]
        return [block.section]

    def _build_heading_anchor(self, section_path: list[str]) -> str:
        joined = "-".join(part.strip().lower() for part in section_path if part.strip())
        compact = _ANCHOR_SAFE_PATTERN.sub("-", joined).strip("-")
        return compact or "untitled-section"

    def _is_protected(self, block: ParsedBlock) -> bool:
        return block.block_type in self.config.protected_block_types
