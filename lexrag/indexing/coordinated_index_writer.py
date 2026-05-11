"""Coordinated dense+sparse indexing with compensating rollback."""

from __future__ import annotations

from collections import defaultdict

from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk
from lexrag.observability.logging_runtime import get_logger

logger = get_logger(__name__)


class CoordinatedIndexWriter:
    """Keep dense and sparse stores consistent for document-level writes."""

    def __init__(
        self,
        *,
        qdrant_store: QdrantStore,
        bm25_store: BM25Store,
    ) -> None:
        self.qdrant_store = qdrant_store
        self.bm25_store = bm25_store

    def index_chunks(self, chunks: list[Chunk]) -> int:
        """Index document chunks with rollback on sparse-write failure."""
        indexed = 0
        for document_id, document_chunks in self._chunks_by_document(chunks).items():
            indexed += self._index_document(
                document_id=document_id,
                chunks=document_chunks,
            )
        return indexed

    def _index_document(self, *, document_id: str, chunks: list[Chunk]) -> int:
        dense_snapshot = self.qdrant_store.list_document_chunks(document_id=document_id)
        sparse_snapshot = self.bm25_store.list_document_chunks(document_id=document_id)
        indexed = self.qdrant_store.upsert_chunks(chunks)
        try:
            self.bm25_store.replace_document_chunks(
                document_id=document_id,
                chunks=chunks,
            )
        except Exception as exc:
            self._rollback_document(
                document_id=document_id,
                dense_snapshot=dense_snapshot,
                sparse_snapshot=sparse_snapshot,
                cause=exc,
            )
            raise
        return indexed

    def _rollback_document(
        self,
        *,
        document_id: str,
        dense_snapshot: list[Chunk],
        sparse_snapshot: list[Chunk],
        cause: Exception,
    ) -> None:
        self.qdrant_store.restore_document_chunks(
            document_id=document_id,
            chunks=dense_snapshot,
        )
        self.bm25_store.restore_document_chunks(
            document_id=document_id,
            chunks=sparse_snapshot,
        )
        logger.exception(
            "Coordinated indexing rolled back document=%s after sparse failure",
            document_id,
            exc_info=cause,
        )

    def _chunks_by_document(self, chunks: list[Chunk]) -> dict[str, list[Chunk]]:
        grouped: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            grouped[self._document_id(chunk=chunk)].append(chunk)
        return grouped

    def _document_id(self, *, chunk: Chunk) -> str:
        return chunk.metadata.doc_id or "unknown_doc"
