"""Production chunking pipeline for normalized parsed blocks."""

from __future__ import annotations

from lexrag.ingestion.chunker.base_chunker import BaseChunker
from lexrag.ingestion.chunker.chunker import Chunker
from lexrag.ingestion.chunker.chunking_pipeline_result import ChunkingPipelineResult
from lexrag.ingestion.chunker.semantic_chunker import SemanticChunker
from lexrag.ingestion.normalized_block_pipeline import NormalizedBlockPipeline
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class ChunkingPipeline(Chunker):
    """Run block curation and chunk materialization as one package component."""

    def __init__(
        self,
        *,
        chunker: Chunker | None = None,
        normalized_block_pipeline: NormalizedBlockPipeline | None = None,
    ) -> None:
        self.chunker = chunker or SemanticChunker()
        self.normalized_block_pipeline = (
            normalized_block_pipeline or NormalizedBlockPipeline()
        )

    def chunk(self, blocks: list[ParsedBlock]):
        """Return canonical chunks for one normalized document block stream."""
        return self.chunk_with_report(blocks).chunks

    def chunk_with_report(
        self,
        blocks: list[ParsedBlock],
    ) -> ChunkingPipelineResult:
        """Return stage-level artifacts for observability and tests."""
        curated = self.normalized_block_pipeline.prepare_result(blocks)
        chunks = self._materialize_chunks(curated.validated_blocks)
        return ChunkingPipelineResult(
            input_blocks=list(blocks),
            curated_blocks=curated,
            chunks=chunks,
            strategy_name=self.chunker.__class__.__name__,
        )

    def _materialize_chunks(self, blocks: list[ParsedBlock]):
        """Avoid repeating block curation when the strategy is BaseChunker-based."""
        if isinstance(self.chunker, BaseChunker):
            return self.chunker.chunk_prepared(blocks)
        return self.chunker.chunk(blocks)
