"""Production semantic chunker aligned with the planning flow."""

from __future__ import annotations

from lexrag.ingestion.chunker.builders.chunk_builder import ChunkBuilder
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.planning.block_aware_semantic_planner import (
    BlockAwareSemanticPlanner,
)
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.strategies.base_chunker import BaseChunker
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class SemanticChunker(BaseChunker):
    """Build semantically coherent chunks without depending on embeddings."""

    def __init__(
        self,
        *,
        config: ChunkingConfig | None = None,
        embedding_mode: str | None = None,
    ) -> None:
        _ = embedding_mode
        super().__init__(config=config)
        self.planner = BlockAwareSemanticPlanner(
            config=self.config,
            tokenization_engine=self.tokenization_engine,
        )
        self.builder = ChunkBuilder(
            config=self.config,
            tokenization_engine=self.tokenization_engine,
            similarity_engine=self.similarity_engine,
        )

    def _chunk_prepared_blocks(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Run planner, builder, factory, and post-processor in order."""
        plans = self.planner.plan(blocks)
        if not plans:
            return []
        raw_chunks = self.builder.build(plans)
        built = self.chunk_model_factory.build_chunks(raw_chunks, parsed_blocks=blocks)
        return self.chunk_post_processor.process(built)
