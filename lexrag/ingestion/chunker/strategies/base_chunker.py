"""Shared base class for chunkers that materialize canonical chunk models."""

from __future__ import annotations

from abc import abstractmethod

from lexrag.ingestion.block_quality import BlockQualityValidator
from lexrag.ingestion.chunker.chunk_post_processor import ChunkPostProcessor
from lexrag.ingestion.chunker.config.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.contracts.chunker import Chunker
from lexrag.ingestion.chunker.factories.chunk_model_factory import ChunkModelFactory
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.support.similarity_engine import SimilarityEngine
from lexrag.ingestion.chunker.support.tokenization_engine import TokenizationEngine
from lexrag.ingestion.deduplicator import BlockDeduplicator
from lexrag.ingestion.normalized_block_pipeline import NormalizedBlockPipeline
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class BaseChunker(Chunker):
    """Provide shared collaborators used by concrete chunker strategies."""

    def __init__(
        self,
        *,
        config: ChunkingConfig | None = None,
        tokenization_engine: TokenizationEngine | None = None,
        chunk_model_factory: ChunkModelFactory | None = None,
        similarity_engine: SimilarityEngine | None = None,
        chunk_post_processor: ChunkPostProcessor | None = None,
        block_deduplicator: BlockDeduplicator | None = None,
        block_quality_validator: BlockQualityValidator | None = None,
        normalized_block_pipeline: NormalizedBlockPipeline | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.tokenization_engine = tokenization_engine or TokenizationEngine()
        self.chunk_model_factory = chunk_model_factory or ChunkModelFactory(
            tokenization_engine=self.tokenization_engine
        )
        self.similarity_engine = similarity_engine or SimilarityEngine()
        self.chunk_post_processor = chunk_post_processor or ChunkPostProcessor(
            config=self.config,
            tokenization_engine=self.tokenization_engine,
        )
        self.normalized_block_pipeline = normalized_block_pipeline or NormalizedBlockPipeline(
            deduplicator=block_deduplicator,
            validator=block_quality_validator,
        )

    def chunk(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Prepare blocks and materialize canonical chunks."""
        return self.chunk_prepared(self._prepare_blocks(blocks=blocks))

    def chunk_prepared(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Chunk blocks that already passed package curation stages."""
        return self._chunk_prepared_blocks(blocks)

    def _prepare_blocks(self, *, blocks: list[ParsedBlock]) -> list[ParsedBlock]:
        """Run block-level quality gates before chunk construction."""
        return self.normalized_block_pipeline.prepare(blocks)

    @abstractmethod
    def _chunk_prepared_blocks(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        """Build canonical chunks from already curated parsed blocks."""
