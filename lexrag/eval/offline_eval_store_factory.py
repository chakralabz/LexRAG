"""Offline in-memory store factory for eval runs."""

from __future__ import annotations

from lexrag.eval.eval_store_factory import EvalStoreFactory
from lexrag.indexing.bm25_store import BM25Store
from lexrag.vector.qdrant_store import QdrantStore


class OfflineEvalStoreFactory(EvalStoreFactory):
    """Builds in-memory stores for fully offline eval runs."""

    def create_dense_store(self, *, collection_name: str) -> QdrantStore:
        return QdrantStore(collection_name=collection_name, backend="memory")

    def create_sparse_store(self, *, index_name: str) -> BM25Store:
        return BM25Store(index_name=index_name, backend="memory")
