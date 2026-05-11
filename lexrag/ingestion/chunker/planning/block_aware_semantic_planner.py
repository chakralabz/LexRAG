"""Planning pass that annotates blocks before chunk construction."""

from __future__ import annotations

from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.config.chunking_strategy import ChunkingStrategy
from lexrag.ingestion.chunker.config.oversized_chunk_strategy import (
    OversizedChunkStrategy,
)
from lexrag.ingestion.chunker.schemas.planned_chunk import PlannedChunk
from lexrag.ingestion.chunker.support.tokenization_engine import TokenizationEngine
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class BlockAwareSemanticPlanner:
    """Assign chunking strategy and boundary signals per normalized block."""

    def __init__(
        self,
        *,
        config: ChunkingConfig | None = None,
        tokenization_engine: TokenizationEngine | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.tokenization_engine = tokenization_engine or TokenizationEngine()

    def plan(self, blocks: list[ParsedBlock]) -> list[PlannedChunk]:
        """Build planner records while dropping blank non-indexable blocks."""
        plans: list[PlannedChunk] = []
        for block in blocks:
            text = block.text.strip()
            if text:
                plans.append(self._plan_block(block=block, text=text))
        return plans

    def _plan_block(self, *, block: ParsedBlock, text: str) -> PlannedChunk:
        """Build one planning record from one parsed block."""
        strategy = self._strategy_for(block=block, token_count=self._tokens(text))
        return PlannedChunk(
            block=block,
            text=text,
            token_count=self._tokens(text),
            chunking_strategy=strategy,
            standalone=strategy in self._standalone_strategies(),
            merge_with_next=strategy not in self._standalone_strategies(),
            overlap_candidate=strategy in self._overlap_candidate_strategies(),
            section_boundary=self._is_section_boundary(block=block, strategy=strategy),
            heading_anchor=self._heading_anchor(block=block),
        )

    def _strategy_for(
        self,
        *,
        block: ParsedBlock,
        token_count: int,
    ) -> ChunkingStrategy:
        """Choose the strategy that best fits the block shape."""
        if block.block_type == "heading":
            return ChunkingStrategy.HEADING_ANCHORED
        if block.block_type == "table":
            return ChunkingStrategy.TABLE_AWARE
        if block.block_type in {"code", "code_block", "definition"}:
            return ChunkingStrategy.STANDALONE
        if block.block_type in self._visual_block_types():
            return ChunkingStrategy.STANDALONE
        if block.block_type == "list":
            return ChunkingStrategy.HEADING_ANCHORED
        if token_count > self.config.max_chunk_tokens:
            return self._oversized_strategy()
        return ChunkingStrategy.SEMANTIC_MERGE

    def _oversized_strategy(self) -> ChunkingStrategy:
        """Map oversized-block policy to a planner-visible strategy."""
        if self.config.oversized_chunk_strategy == OversizedChunkStrategy.RECURSIVE:
            return ChunkingStrategy.RECURSIVE_WINDOW
        return ChunkingStrategy.SLIDING_WINDOW

    def _is_section_boundary(
        self,
        *,
        block: ParsedBlock,
        strategy: ChunkingStrategy,
    ) -> bool:
        """Detect boundaries that should flush the current semantic buffer."""
        if strategy == ChunkingStrategy.HEADING_ANCHORED:
            return True
        if block.heading_level is not None:
            return True
        return bool(block.is_ocr and (block.confidence or 1.0) < 0.50)

    def _heading_anchor(self, *, block: ParsedBlock) -> str | None:
        """Resolve stable heading context for downstream chunk lineage."""
        anchor = block.metadata.get("heading_anchor")
        if isinstance(anchor, str) and anchor.strip():
            return anchor.strip()
        if block.block_type == "heading" and block.text.strip():
            return block.text.strip()
        if block.section.strip():
            return block.section.strip()
        return None

    def _tokens(self, text: str) -> int:
        """Count tokens using the shared tokenizer."""
        return self.tokenization_engine.count_tokens(text)

    def _standalone_strategies(self) -> set[ChunkingStrategy]:
        """Return strategies that must not merge with neighbors."""
        return {ChunkingStrategy.STANDALONE, ChunkingStrategy.TABLE_AWARE}

    def _overlap_candidate_strategies(self) -> set[ChunkingStrategy]:
        """Return strategies where overlap may be helpful downstream."""
        return {
            ChunkingStrategy.RECURSIVE_WINDOW,
            ChunkingStrategy.SEMANTIC_MERGE,
            ChunkingStrategy.SLIDING_WINDOW,
        }

    def _visual_block_types(self) -> set[str]:
        """Return parser block types that should stay isolated."""
        return {"caption", "image", "image_caption", "table_caption"}
