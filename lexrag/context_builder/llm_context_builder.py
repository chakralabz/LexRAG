"""High-level orchestrator for the generation context window."""

from __future__ import annotations

from collections.abc import Mapping

from lexrag.citation import CitationDocument, CitationResolver
from lexrag.citation.schemas import ResolvedCitation
from lexrag.context_builder.context_conflict_detector import ContextConflictDetector
from lexrag.context_builder.context_prompt_formatter import ContextPromptFormatter
from lexrag.context_builder.context_window_compressor import ContextWindowCompressor
from lexrag.context_builder.context_window_deduplicator import ContextWindowDeduplicator
from lexrag.context_builder.context_window_orderer import ContextWindowOrderer
from lexrag.context_builder.schemas import (
    ContextBuilderConfig,
    ContextSource,
    ContextWindow,
)
from lexrag.indexing.schemas import Chunk
from lexrag.utils.text import TextNormalizer


class LLMContextBuilder:
    """Build a safe, compact prompt context from reranked retrieval output."""

    def __init__(
        self,
        *,
        config: ContextBuilderConfig | None = None,
        citation_resolver: CitationResolver | None = None,
        deduplicator: ContextWindowDeduplicator | None = None,
        orderer: ContextWindowOrderer | None = None,
        conflict_detector: ContextConflictDetector | None = None,
        compressor: ContextWindowCompressor | None = None,
        formatter: ContextPromptFormatter | None = None,
    ) -> None:
        self.config = config or ContextBuilderConfig()
        self.citation_resolver = citation_resolver or CitationResolver()
        self.deduplicator = deduplicator or ContextWindowDeduplicator(
            config=self.config
        )
        self.orderer = orderer or ContextWindowOrderer(config=self.config)
        self.conflict_detector = conflict_detector or ContextConflictDetector(
            config=self.config
        )
        self.compressor = compressor or ContextWindowCompressor(config=self.config)
        self.formatter = formatter or ContextPromptFormatter(config=self.config)
        self.normalizer = TextNormalizer()

    def build(
        self,
        *,
        query: str,
        chunks: list[Chunk],
        document_catalog: Mapping[str, CitationDocument] | None = None,
    ) -> ContextWindow:
        """Produce a generation-ready context window for one question."""

        resolution = self.citation_resolver.resolve(
            chunks,
            document_catalog=document_catalog,
        )
        sources = self._sources(
            chunks=chunks, resolution_by_chunk_id=resolution.by_chunk_id()
        )
        deduplicated = self.deduplicator.deduplicate(sources)
        ordered = self.orderer.order(deduplicated)
        compressed = self.compressor.compress(query=query, sources=ordered)
        warnings = self.conflict_detector.detect(compressed)
        return self.formatter.format(query=query, sources=compressed, warnings=warnings)

    def _sources(
        self,
        *,
        chunks: list[Chunk],
        resolution_by_chunk_id: Mapping[str, ResolvedCitation],
    ) -> list[ContextSource]:
        """Attach citation metadata to each retained chunk."""

        return [
            ContextSource(
                chunk=chunk,
                citation=resolution_by_chunk_id[chunk.chunk_id],
                rank_score=self._rank_score(chunk=chunk),
                quality_score=self._quality_score(chunk=chunk),
                token_count=len(self.normalizer.tokenize_non_whitespace(chunk.text)),
            )
            for chunk in chunks
            if chunk.chunk_id in resolution_by_chunk_id
        ]

    def _rank_score(self, *, chunk: Chunk) -> float:
        """Read the strongest available query-time score from metadata."""

        payload = chunk.metadata.metadata.get(
            "reranker"
        ) or chunk.metadata.metadata.get("retrieval", {})
        return float(payload.get("score", 0.0))

    def _quality_score(self, *, chunk: Chunk) -> float:
        """Read a chunk quality score suitable for compression decisions."""

        if chunk.metadata.chunk_quality_score is not None:
            return float(chunk.metadata.chunk_quality_score)
        return 0.0
