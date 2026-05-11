"""Dense vector store facade with production-grade upsert semantics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from lexrag.indexing.backends import InMemoryQdrantBackend, QdrantServiceBackend
from lexrag.indexing.backends.dense_store_backend import DenseStoreBackend
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.observability.logging_runtime import get_logger
from lexrag.vector.index_optimizer import IndexOptimizer
from lexrag.vector.reindex_planner import ReindexPlanner
from lexrag.vector.schemas import (
    IndexOptimizationReport,
    ReindexPlan,
    VectorIndexConfig,
    VectorUpsertReport,
)
from lexrag.vector.vector_deduplicator import VectorDeduplicator

logger = get_logger(__name__)


class QdrantStore:
    """Owns vector deduplication, re-index planning, and backend writes.

    Backends remain storage-centric. This facade enforces architecture rules:
    deterministic chunk IDs, dimension validation, version-aware replacement,
    vector-level deduplication, and index optimization.
    """

    def __init__(
        self,
        *,
        collection_name: str = "lexrag_chunks",
        backend: str = "qdrant",
        vector_size: int | None = None,
        qdrant_url: str = "http://localhost:6333",
        api_key: str | None = None,
        vector_deduplicator: VectorDeduplicator | None = None,
        optimizer: IndexOptimizer | None = None,
        reindex_planner: ReindexPlanner | None = None,
    ) -> None:
        self.config = VectorIndexConfig(
            collection_name=collection_name,
            backend=backend,
            vector_size=vector_size,
            qdrant_url=qdrant_url,
            api_key=api_key,
        )
        self.vector_deduplicator = vector_deduplicator or VectorDeduplicator()
        self.optimizer = optimizer or IndexOptimizer()
        self.reindex_planner = reindex_planner or ReindexPlanner()
        self.backend = self._build_backend()
        self.last_upsert_report = self._empty_report()
        self.optimization_report = self._initialize_optimization_report()

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Write chunks with validation, deduplication, and version safety."""

        if not chunks:
            self.last_upsert_report = self._empty_report()
            return 0
        self._validate_embeddings(chunks=chunks)
        deduplicated = self._deduplicate(chunks=chunks)
        indexed, replaced, rolled_back, plans = self._write_documents(
            chunks=deduplicated
        )
        self._ensure_backend_optimized()
        self.last_upsert_report = self._build_report(
            attempted=chunks,
            indexed=deduplicated,
            indexed_count=indexed,
            replaced_chunks=replaced,
            rollback_performed=rolled_back,
            reindex_plans=plans,
        )
        return indexed

    def search_dense(
        self,
        query_vector: list[float],
        *,
        limit: int = 10,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Run dense retrieval with optional metadata filters."""

        return self.backend.search_dense(
            query_vector,
            limit=limit,
            metadata_filters=metadata_filters,
        )

    def delete_collection(self) -> None:
        """Delete all data from the active dense collection."""

        self.backend.delete_collection()

    def count(self) -> int:
        """Return indexed chunk count."""

        return self.backend.count()

    def list_document_chunks(self, *, document_id: str) -> list[Chunk]:
        """Return all dense chunks for one document."""
        return self.backend.list_chunks(metadata_filters={"doc_id": document_id})

    def restore_document_chunks(self, *, document_id: str, chunks: list[Chunk]) -> None:
        """Restore one document to an exact dense snapshot."""
        existing = self.list_document_chunks(document_id=document_id)
        if existing:
            self.backend.delete_chunks([chunk.chunk_id for chunk in existing])
        if chunks:
            self._validate_embeddings(chunks=chunks)
            self.backend.upsert_chunks(chunks)

    def _build_backend(self) -> DenseStoreBackend:
        if self.config.backend == "memory":
            return InMemoryQdrantBackend()
        if self.config.backend == "qdrant":
            return QdrantServiceBackend(
                collection_name=self.config.collection_name,
                vector_size=self.config.vector_size,
                qdrant_url=self.config.qdrant_url,
                api_key=self.config.api_key,
            )
        raise ValueError(f"Unsupported dense backend: {self.config.backend!r}")

    def _validate_embeddings(self, *, chunks: list[Chunk]) -> None:
        expected_size = self._expected_vector_size(chunks=chunks)
        for chunk in chunks:
            embedding = chunk.embedding
            if embedding is None:
                raise ValueError(f"Chunk {chunk.chunk_id} is missing embedding")
            if len(embedding) != expected_size:
                raise ValueError(
                    f"Chunk {chunk.chunk_id} has embedding dim {len(embedding)} "
                    f"but store expects {expected_size}"
                )

    def _expected_vector_size(self, *, chunks: list[Chunk]) -> int:
        if self.config.vector_size is not None:
            return self.config.vector_size
        first_embedding = chunks[0].embedding or []
        if not first_embedding:
            raise ValueError("Cannot infer vector size from empty embedding")
        return len(first_embedding)

    def _deduplicate(self, *, chunks: list[Chunk]) -> list[Chunk]:
        existing = self._existing_chunks_for(chunks=chunks)
        return self.vector_deduplicator.deduplicate(chunks, existing_chunks=existing)

    def _existing_chunks_for(self, *, chunks: list[Chunk]) -> list[Chunk]:
        existing_by_id: dict[str, Chunk] = {}
        for chunk in chunks:
            for candidate in self._dedup_candidates_for(chunk=chunk):
                existing_by_id[candidate.chunk_id] = candidate
        return list(existing_by_id.values())

    def _dedup_candidates_for(self, *, chunk: Chunk) -> list[Chunk]:
        candidates: dict[str, Chunk] = {}
        for candidate in self._lineage_candidates(chunk=chunk):
            candidates[candidate.chunk_id] = candidate
        for candidate in self._semantic_candidates(chunk=chunk):
            candidates[candidate.chunk_id] = candidate
        candidates.pop(chunk.chunk_id, None)
        return list(candidates.values())

    def _lineage_candidates(self, *, chunk: Chunk) -> list[Chunk]:
        document_id = chunk.metadata.doc_id
        if document_id is None:
            return []
        return self.backend.list_chunks(metadata_filters={"doc_id": document_id})

    def _semantic_candidates(self, *, chunk: Chunk) -> list[Chunk]:
        return self.backend.search_dense(
            chunk.embedding or [],
            limit=self.vector_deduplicator.config.candidate_pool_size,
            metadata_filters=None,
        )

    def _write_documents(
        self,
        *,
        chunks: list[Chunk],
    ) -> tuple[int, int, bool, list[ReindexPlan]]:
        indexed_total = 0
        replaced_total = 0
        rollback_performed = False
        plans: list[ReindexPlan] = []
        for document_chunks in self._chunks_by_document(chunks=chunks).values():
            indexed, replaced, rolled_back, plan = self._write_document(
                chunks=document_chunks
            )
            indexed_total += indexed
            replaced_total += replaced
            rollback_performed = rollback_performed or rolled_back
            plans.append(plan)
        return indexed_total, replaced_total, rollback_performed, plans

    def _chunks_by_document(self, *, chunks: list[Chunk]) -> dict[str, list[Chunk]]:
        grouped: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.metadata.doc_id or "unknown_doc"].append(chunk)
        return grouped

    def _write_document(
        self,
        *,
        chunks: list[Chunk],
    ) -> tuple[int, int, bool, ReindexPlan]:
        existing = self._existing_document_chunks(chunks=chunks)
        plan = self.reindex_planner.plan(incoming=chunks, existing=existing)
        indexed = self.backend.upsert_chunks(chunks)
        rolled_back = self._finalize_document_replace(
            new_chunks=chunks,
            stale_ids=plan.stale_chunk_ids,
            existing=existing,
        )
        return indexed, len(plan.stale_chunk_ids), rolled_back, plan

    def _existing_document_chunks(self, *, chunks: list[Chunk]) -> list[Chunk]:
        document_id = chunks[0].metadata.doc_id
        if document_id is None:
            return []
        return self.backend.list_chunks(metadata_filters={"doc_id": document_id})

    def _finalize_document_replace(
        self,
        *,
        new_chunks: list[Chunk],
        stale_ids: list[str],
        existing: list[Chunk],
    ) -> bool:
        if not stale_ids:
            return False
        stale_chunks = [chunk for chunk in existing if chunk.chunk_id in stale_ids]
        try:
            deleted = self.backend.delete_chunks(stale_ids)
            if deleted != len(stale_ids):
                raise RuntimeError(
                    "Dense backend deleted fewer stale chunks than planned"
                )
        except Exception as exc:
            self._rollback_document_replace(
                new_chunks=new_chunks,
                stale_chunks=stale_chunks,
                cause=exc,
            )
            raise
        return False

    def _rollback_document_replace(
        self,
        *,
        new_chunks: list[Chunk],
        stale_chunks: list[Chunk],
        cause: Exception,
    ) -> None:
        """Restore pre-write state after stale-chunk cleanup fails."""
        self._delete_new_chunks(new_chunks=new_chunks)
        self.backend.upsert_chunks(stale_chunks)
        logger.exception(
            "Vector stale-chunk cleanup failed; restored prior document state",
            exc_info=cause,
        )

    def _delete_new_chunks(self, *, new_chunks: list[Chunk]) -> None:
        """Remove newly written chunk IDs during rollback."""
        new_ids = [chunk.chunk_id for chunk in new_chunks]
        deleted = self.backend.delete_chunks(new_ids)
        if deleted != len(new_ids):
            raise RuntimeError("Dense rollback failed to remove newly written chunks")

    def _build_report(
        self,
        *,
        attempted: list[Chunk],
        indexed: list[Chunk],
        indexed_count: int,
        replaced_chunks: int,
        rollback_performed: bool,
        reindex_plans: list[ReindexPlan],
    ) -> VectorUpsertReport:
        return VectorUpsertReport(
            attempted_chunks=len(attempted),
            indexed_chunks=indexed_count,
            suppressed_chunks=len(attempted) - len(indexed),
            replaced_chunks=replaced_chunks,
            rollback_performed=rollback_performed,
            document_ids=self._document_ids(chunks=indexed),
            reindex_plans=reindex_plans,
        )

    def _document_ids(self, *, chunks: list[Chunk]) -> list[str]:
        return sorted({chunk.metadata.doc_id or "unknown_doc" for chunk in chunks})

    def _empty_report(self) -> VectorUpsertReport:
        return VectorUpsertReport(
            attempted_chunks=0,
            indexed_chunks=0,
            suppressed_chunks=0,
            replaced_chunks=0,
            rollback_performed=False,
            document_ids=[],
            reindex_plans=[],
        )

    def _initialize_optimization_report(self) -> IndexOptimizationReport | None:
        if self.config.backend == "qdrant" and self.config.vector_size is None:
            return None
        return self.optimizer.optimize_dense(backend=self.backend)

    def _ensure_backend_optimized(self) -> None:
        if self.optimization_report is not None:
            return
        self.optimization_report = self.optimizer.optimize_dense(backend=self.backend)
