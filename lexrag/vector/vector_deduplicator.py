"""Vector-level semantic deduplication for indexed chunks."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.observability.logging_runtime import get_logger
from lexrag.vector.schemas import (
    VectorDeduplicationConfig,
    VectorDeduplicationDecision,
    VectorDeduplicationReport,
)
from lexrag.vector.vector_similarity_engine import VectorSimilarityEngine

logger = get_logger(__name__)


class VectorDeduplicator:
    """Suppresses duplicate vectors without erasing source provenance.

    The architecture keeps same-lineage suppression conservative and treats
    cross-document similarity as an audit signal, not a deletion trigger. That
    preserves citation provenance even when two documents say nearly the same
    thing.
    """

    def __init__(
        self,
        *,
        config: VectorDeduplicationConfig | None = None,
        similarity_engine: VectorSimilarityEngine | None = None,
    ) -> None:
        self.config = config or VectorDeduplicationConfig()
        self.similarity_engine = similarity_engine or VectorSimilarityEngine()
        self.last_report = VectorDeduplicationReport()

    def deduplicate(
        self,
        chunks: list[Chunk],
        *,
        existing_chunks: list[Chunk] | None = None,
    ) -> list[Chunk]:
        """Return chunks that should proceed to storage.

        Args:
            chunks: Newly embedded chunks under evaluation.
            existing_chunks: Candidate comparison set loaded from the vector
                index.

        Returns:
            Chunks that survive vector-level deduplication.
        """

        kept: list[Chunk] = []
        decisions: list[VectorDeduplicationDecision] = []
        baseline = list(existing_chunks or [])
        for chunk in chunks:
            self._validate_chunk(chunk=chunk)
            decision = self._decision_for(chunk=chunk, baseline=baseline, kept=kept)
            decisions.append(decision)
            if decision.decision != "suppressed":
                kept.append(chunk)
        self.last_report = VectorDeduplicationReport(decisions=decisions)
        self._log_summary(total=len(chunks), kept=len(kept))
        return kept

    def _decision_for(
        self,
        *,
        chunk: Chunk,
        baseline: list[Chunk],
        kept: list[Chunk],
    ) -> VectorDeduplicationDecision:
        same_lineage = self._best_match(
            chunk=chunk,
            candidates=[*baseline, *kept],
            require_same_doc_id=True,
        )
        if self._should_suppress(match=same_lineage):
            return self._suppressed_decision(chunk=chunk, match=same_lineage)
        cross_document = self._best_match(
            chunk=chunk,
            candidates=[*baseline, *kept],
            require_same_doc_id=False,
        )
        if self._is_cross_document_match(chunk=chunk, match=cross_document):
            return self._cross_document_decision(chunk=chunk, match=cross_document)
        return self._kept_decision(chunk=chunk)

    def _best_match(
        self,
        *,
        chunk: Chunk,
        candidates: list[Chunk],
        require_same_doc_id: bool,
    ) -> tuple[Chunk, float] | None:
        best_match: tuple[Chunk, float] | None = None
        for candidate in candidates:
            if not self._eligible_candidate(
                chunk=chunk,
                candidate=candidate,
                require_same_doc_id=require_same_doc_id,
            ):
                continue
            similarity = self._similarity(chunk=chunk, candidate=candidate)
            if best_match is None or similarity > best_match[1]:
                best_match = (candidate, similarity)
        return best_match

    def _eligible_candidate(
        self,
        *,
        chunk: Chunk,
        candidate: Chunk,
        require_same_doc_id: bool,
    ) -> bool:
        if candidate.chunk_id == chunk.chunk_id:
            return False
        if require_same_doc_id:
            return self._same_suppression_scope(chunk=chunk, candidate=candidate)
        return not self._same_document_lineage(chunk=chunk, candidate=candidate)

    def _same_document_lineage(self, *, chunk: Chunk, candidate: Chunk) -> bool:
        if not self.config.require_matching_doc_id_for_suppression:
            return True
        return candidate.metadata.doc_id == chunk.metadata.doc_id

    def _same_suppression_scope(self, *, chunk: Chunk, candidate: Chunk) -> bool:
        if not self._same_document_lineage(chunk=chunk, candidate=candidate):
            return False
        return (
            candidate.metadata.document_version == chunk.metadata.document_version
            or candidate.metadata.document_version is None
            or chunk.metadata.document_version is None
        )

    def _similarity(self, *, chunk: Chunk, candidate: Chunk) -> float:
        return self.similarity_engine.cosine_similarity(
            chunk.embedding or [],
            candidate.embedding or [],
        )

    def _should_suppress(self, *, match: tuple[Chunk, float] | None) -> bool:
        if match is None:
            return False
        return match[1] >= self.config.within_document_similarity_threshold

    def _is_cross_document_match(
        self,
        *,
        chunk: Chunk,
        match: tuple[Chunk, float] | None,
    ) -> bool:
        if match is None:
            return False
        return match[1] >= self.config.cross_document_similarity_threshold

    def _kept_decision(self, *, chunk: Chunk) -> VectorDeduplicationDecision:
        return VectorDeduplicationDecision(
            chunk_id=chunk.chunk_id,
            decision="kept",
            reason="no_semantic_duplicate_detected",
        )

    def _suppressed_decision(
        self,
        *,
        chunk: Chunk,
        match: tuple[Chunk, float] | None,
    ) -> VectorDeduplicationDecision:
        matched_chunk, similarity = match or (chunk, 0.0)
        return VectorDeduplicationDecision(
            chunk_id=chunk.chunk_id,
            decision="suppressed",
            matched_chunk_id=matched_chunk.chunk_id,
            matched_doc_id=matched_chunk.metadata.doc_id,
            similarity=similarity,
            reason="same_document_semantic_duplicate",
        )

    def _cross_document_decision(
        self,
        *,
        chunk: Chunk,
        match: tuple[Chunk, float] | None,
    ) -> VectorDeduplicationDecision:
        matched_chunk, similarity = match or (chunk, 0.0)
        return VectorDeduplicationDecision(
            chunk_id=chunk.chunk_id,
            decision="cross_document_match",
            matched_chunk_id=matched_chunk.chunk_id,
            matched_doc_id=matched_chunk.metadata.doc_id,
            similarity=similarity,
            reason="kept_distinct_provenance",
        )

    def _validate_chunk(self, *, chunk: Chunk) -> None:
        if chunk.embedding is None:
            raise ValueError(
                f"Chunk {chunk.chunk_id} is missing embedding for vector deduplication"
            )

    def _log_summary(self, *, total: int, kept: int) -> None:
        logger.info(
            "Vector dedup finished: total_seen=%d total_suppressed=%d kept=%d",
            total,
            total - kept,
            kept,
        )
