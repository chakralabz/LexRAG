"""Reusable package-level RAG ingestion and retrieval pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.indexing.bm25_store import BM25Store
from lexrag.indexing.coordinated_index_writer import CoordinatedIndexWriter
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.embeddings.embedding_preparation_service import (
    EmbeddingPreparationService,
)
from lexrag.ingestion.file_ingestion.file_validation_service import (
    FileValidationService,
)
from lexrag.retrieval.base import Retriever
from lexrag.services.audit_service import AuditService
from lexrag.services.block_normalization_service import BlockNormalizationService
from lexrag.services.chunking_service import ChunkingService
from lexrag.services.deduplication_service import DeduplicationService
from lexrag.services.embedding_service import EmbeddingService
from lexrag.services.observability_service import ObservabilityService
from lexrag.services.parser_service import ParserService
from lexrag.services.vector_preparation_service import VectorPreparationService


class RAGPipeline:
    """Compose reusable ingestion services into one SDK pipeline."""

    def __init__(
        self,
        *,
        file_validation_service: FileValidationService | None = None,
        parser_service: ParserService | None = None,
        block_normalization_service: BlockNormalizationService | None = None,
        deduplication_service: DeduplicationService | None = None,
        chunking_service: ChunkingService | None = None,
        embedding_preparation_service: EmbeddingPreparationService | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_preparation_service: VectorPreparationService | None = None,
        audit_service: AuditService | None = None,
        observability_service: ObservabilityService | None = None,
        retriever: Retriever | None = None,
        qdrant_store: QdrantStore | None = None,
        bm25_store: BM25Store | None = None,
    ) -> None:
        self.file_validation_service = (
            file_validation_service or FileValidationService()
        )
        self.parser_service = parser_service or ParserService()
        self.block_normalization_service = (
            block_normalization_service or BlockNormalizationService()
        )
        self.deduplication_service = deduplication_service or DeduplicationService()
        self.chunking_service = chunking_service or ChunkingService()
        self.embedding_preparation_service = (
            embedding_preparation_service or EmbeddingPreparationService()
        )
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_preparation_service = (
            vector_preparation_service or VectorPreparationService()
        )
        self.audit_service = audit_service or AuditService()
        self.observability_service = observability_service or ObservabilityService()
        self.retriever = retriever
        self.qdrant_store = qdrant_store
        self.bm25_store = bm25_store
        self.index_writer = self._build_index_writer()

    def load(self) -> RAGPipeline:
        """Preload heavy runtimes for startup-time initialization."""
        self.observability_service.configure()
        self.parser_service.load()
        self.embedding_service.load()
        return self

    def close(self) -> None:
        """Tear down managed heavyweight runtimes."""
        self.parser_service.close()
        self.embedding_service.close()

    def ingest(self, paths: list[str | Path]) -> list[Chunk]:
        """Run the full ingestion pipeline and optionally index outputs."""
        valid_paths = self._validated_paths(paths=paths)
        chunks = self._chunk_documents(paths=valid_paths)
        prepared = self.prepare_embeddings(chunks)
        embedded = self.embedding_service.embed_prepared_chunks(prepared)
        deduplicated = self.deduplicate_vectors(embedded)
        self._index_chunks(chunks=deduplicated)
        self._audit_chunks(chunks=deduplicated)
        return deduplicated

    def prepare_embeddings(self, chunks: list[Chunk]) -> list[Chunk]:
        """Prepare chunks for embedding generation."""
        return self.embedding_preparation_service.prepare_chunks(chunks)

    def embed(self, chunks: list[Chunk]) -> list[Chunk]:
        """Embed canonical chunks using the managed embedding runtime."""
        return self.embedding_service.embed_chunks(chunks)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Retrieve ranked chunks with the configured retriever."""
        if self.retriever is None:
            raise RuntimeError("RAGPipeline requires a retriever for query execution")
        return self.retriever.retrieve(
            query,
            top_k=top_k,
            metadata_filters=metadata_filters,
        )

    def build_dense_payloads(self, chunks: list[Chunk]) -> list[dict[str, object]]:
        """Serialize chunks for dense vector store ingestion."""
        return self.vector_preparation_service.build_dense_payloads(chunks)

    def build_sparse_documents(self, chunks: list[Chunk]) -> list[dict[str, object]]:
        """Serialize chunks for sparse index ingestion."""
        return self.vector_preparation_service.build_sparse_documents(chunks)

    def deduplicate_vectors(self, chunks: list[Chunk]) -> list[Chunk]:
        """Run vector-level deduplication over embedded chunks."""
        return self.deduplication_service.deduplicate_vectors(chunks)

    def _validated_paths(self, *, paths: list[str | Path]) -> list[Path]:
        results = self.file_validation_service.validate_many(_as_paths(paths))
        return [Path(result.path) for result in results if result.is_valid]

    def _chunk_documents(self, *, paths: list[Path]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for path in paths:
            chunks.extend(self._chunk_document(path=path))
        return chunks

    def _chunk_document(self, *, path: Path) -> list[Chunk]:
        blocks = self.parser_service.parse_document(path)
        normalized = self.block_normalization_service.normalize(blocks)
        unique = self.deduplication_service.deduplicate_blocks(normalized)
        return self.chunking_service.chunk(unique)

    def _index_chunks(self, *, chunks: list[Chunk]) -> None:
        if self.index_writer is not None:
            self.index_writer.index_chunks(chunks)
            return
        if self.qdrant_store is not None:
            self.qdrant_store.upsert_chunks(chunks)
        if self.bm25_store is not None:
            self.bm25_store.index_chunks(chunks)

    def _audit_chunks(self, *, chunks: list[Chunk]) -> None:
        results = self.audit_service.validate_chunks(chunks)
        invalid = [result.subject_id for result in results if not result.passed]
        if not invalid:
            return
        self.observability_service.record_event(
            "audit_validation_failed",
            metadata={"invalid_chunk_ids": invalid},
        )

    def _build_index_writer(self) -> CoordinatedIndexWriter | None:
        if self.qdrant_store is None or self.bm25_store is None:
            return None
        return CoordinatedIndexWriter(
            qdrant_store=self.qdrant_store,
            bm25_store=self.bm25_store,
        )


def _as_paths(paths: list[str | Path]) -> list[Path]:
    """Normalize mixed path inputs into concrete ``Path`` objects."""
    return [Path(path) for path in paths]
