"""Document-level block normalization orchestrator."""

from __future__ import annotations

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.normalizer.code_block_normalizer import CodeBlockNormalizer
from lexrag.ingestion.normalizer.heading_normalizer import HeadingNormalizer
from lexrag.ingestion.normalizer.metadata_enricher import MetadataEnricher
from lexrag.ingestion.normalizer.ocr_normalizer import OCRNormalizer
from lexrag.ingestion.normalizer.parser_artifact_cleaner import ParserArtifactCleaner
from lexrag.ingestion.normalizer.schemas import (
    BlockNormalizationConfig,
    build_block_normalization_config,
)
from lexrag.ingestion.normalizer.section_path_normalizer import SectionPathNormalizer
from lexrag.ingestion.normalizer.table_normalizer import TableNormalizer
from lexrag.ingestion.normalizer.text_normalizer import TextNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class BlockNormalizer:
    """Runs the architecture-defined normalization pipeline for one document.

    The stage order mirrors ``docs/architecture.md`` so that parser artifacts
    are removed before structural lineage is inferred, protected block types are
    normalized with their domain-specific rules, and common metadata is emitted
    only after the block content has reached its canonical form.
    """

    def __init__(
        self,
        *,
        config: BlockNormalizationConfig | None = None,
        normalizers: list[BaseNormalizer] | None = None,
    ) -> None:
        self.config = config or build_block_normalization_config()
        self.normalizers = normalizers or self._build_default_normalizers()

    def normalize(self, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Normalizes a document's parsed blocks in a deterministic order.

        Args:
            blocks: Parsed blocks emitted by the parsing layer for one document.

        Returns:
            The normalized block list with dropped or empty artifacts removed.
        """
        if not blocks:
            return []
        self._reset_stateful_normalizers()
        normalized_blocks: list[ParsedBlock] = []
        for block in blocks:
            normalized_block = self._normalize_single_block(block)
            if normalized_block is None:
                continue
            if normalized_block.text.strip():
                normalized_blocks.append(normalized_block)
        return normalized_blocks

    def _build_default_normalizers(self) -> list[BaseNormalizer]:
        return [
            ParserArtifactCleaner(self.config),
            HeadingNormalizer(self.config),
            SectionPathNormalizer(self.config),
            CodeBlockNormalizer(self.config),
            TableNormalizer(self.config),
            OCRNormalizer(self.config),
            TextNormalizer(self.config),
            MetadataEnricher(self.config),
        ]

    def _reset_stateful_normalizers(self) -> None:
        for normalizer in self.normalizers:
            normalizer.reset()

    def _normalize_single_block(self, block: ParsedBlock) -> ParsedBlock | None:
        current: ParsedBlock | None = block
        for normalizer in self.normalizers:
            if current is None:
                return None
            current = normalizer.normalize(current)
            if normalizer.should_drop(current):
                return None
        return current
