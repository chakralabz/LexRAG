"""Abstract store factory for eval application composition."""

from __future__ import annotations

from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore


class EvalStoreFactory:
    """Abstract store factory used by eval application."""

    def create_dense_store(self, *, collection_name: str) -> QdrantStore:
        raise NotImplementedError

    def create_sparse_store(self, *, index_name: str) -> BM25Store:
        raise NotImplementedError
