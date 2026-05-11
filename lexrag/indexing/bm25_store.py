"""Sparse index facade with clean backend selection and optimization."""

from __future__ import annotations

from typing import Any

from lexrag.indexing.backends import ElasticsearchBM25Backend, InMemoryBM25Backend
from lexrag.indexing.backends.sparse_store_backend import SparseStoreBackend
from lexrag.indexing.optimization import IndexOptimizer
from lexrag.indexing.schemas.sparse_index_config import SparseIndexConfig
from lexrag.ingestion.chunker.schemas.chunk import Chunk


class BM25Store:
    """Production-facing lexical store for sparse retrieval."""

    def __init__(
        self,
        *,
        index_name: str = "lexrag_chunks",
        backend: str = "elasticsearch",
        elasticsearch_url: str = "http://localhost:9200",
        optimizer: IndexOptimizer | None = None,
    ) -> None:
        self.config = SparseIndexConfig(
            index_name=index_name,
            backend=backend,
            elasticsearch_url=elasticsearch_url,
        )
        self.optimizer = optimizer or IndexOptimizer()
        self.backend = self._build_backend()
        self.optimization_report = self.optimizer.optimize_sparse(backend=self.backend)

    def index_chunks(self, chunks: list[Chunk]) -> int:
        """Write chunks into the sparse backend."""

        return self.backend.index_chunks(chunks)

    def search_bm25(
        self,
        query: str,
        *,
        limit: int = 10,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Run keyword retrieval with optional metadata filters."""

        return self.backend.search_bm25(
            query,
            limit=limit,
            metadata_filters=metadata_filters,
        )

    def list_document_chunks(self, *, document_id: str) -> list[Chunk]:
        """Return all sparse chunks for one document."""
        return self.backend.list_chunks(metadata_filters={"doc_id": document_id})

    def replace_document_chunks(self, *, document_id: str, chunks: list[Chunk]) -> int:
        """Atomically replace sparse chunks for one document."""
        stale_ids = self._stale_chunk_ids(document_id=document_id)
        if stale_ids:
            self.backend.delete_chunks(stale_ids)
        return self.backend.index_chunks(chunks)

    def count(self) -> int:
        """Return indexed chunk count."""

        return self.backend.count()

    def restore_document_chunks(self, *, document_id: str, chunks: list[Chunk]) -> None:
        """Restore a document to an exact sparse snapshot."""
        stale_ids = self._stale_chunk_ids(document_id=document_id)
        if stale_ids:
            self.backend.delete_chunks(stale_ids)
        if chunks:
            self.backend.index_chunks(chunks)

    def _build_backend(self) -> SparseStoreBackend:
        if self.config.backend == "memory":
            return InMemoryBM25Backend()
        if self.config.backend == "elasticsearch":
            return ElasticsearchBM25Backend(
                index_name=self.config.index_name,
                elasticsearch_url=self.config.elasticsearch_url,
            )
        raise ValueError(f"Unsupported sparse backend: {self.config.backend!r}")

    def _stale_chunk_ids(self, *, document_id: str) -> list[str]:
        stale = self.list_document_chunks(document_id=document_id)
        return [chunk.chunk_id for chunk in stale]
