"""Public vector serialization service."""

from __future__ import annotations

from lexrag.indexing.backends.bm25_document_mapper import build_document
from lexrag.indexing.backends.qdrant_payload_mapper import build_payload
from lexrag.indexing.schemas import Chunk


class VectorPreparationService:
    """Serialize chunks into backend-safe dense and sparse payloads."""

    def build_dense_payloads(self, chunks: list[Chunk]) -> list[dict[str, object]]:
        """Serialize canonical chunks for dense vector stores."""
        return [build_payload(chunk=chunk) for chunk in chunks]

    def build_sparse_documents(self, chunks: list[Chunk]) -> list[dict[str, object]]:
        """Serialize canonical chunks for sparse search indexes."""
        return [build_document(chunk=chunk) for chunk in chunks]
