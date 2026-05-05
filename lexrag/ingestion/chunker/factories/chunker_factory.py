"""Factory for constructing configured chunker implementations."""

from __future__ import annotations

from lexrag.ingestion.chunker.config.chunker_kind import ChunkerKind
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.contracts.chunker import Chunker
from lexrag.ingestion.chunker.strategies.fixed_size_chunker import FixedSizeChunker
from lexrag.ingestion.chunker.strategies.semantic_chunker import SemanticChunker


class ChunkerFactory:
    """Build chunkers from typed configuration instead of ad hoc branching."""

    def build(
        self,
        *,
        config: ChunkingConfig,
        kind: ChunkerKind | None = None,
    ) -> Chunker:
        """Build the requested chunker kind with shared configuration."""
        resolved_kind = kind or config.default_chunker
        if resolved_kind == ChunkerKind.FIXED:
            return FixedSizeChunker(config=config)
        return SemanticChunker(config=config)
