"""Backend exports for the indexing layer."""

from __future__ import annotations

from lexrag.indexing.backends.dense_store_backend import DenseStoreBackend
from lexrag.indexing.backends.elasticsearch_bm25_backend import (
    ElasticsearchBM25Backend,
)
from lexrag.indexing.backends.in_memory_bm25_backend import InMemoryBM25Backend
from lexrag.indexing.backends.in_memory_qdrant_backend import InMemoryQdrantBackend
from lexrag.indexing.backends.qdrant_service_backend import QdrantServiceBackend
from lexrag.indexing.backends.sparse_store_backend import SparseStoreBackend

__all__ = [
    "DenseStoreBackend",
    "ElasticsearchBM25Backend",
    "InMemoryBM25Backend",
    "InMemoryQdrantBackend",
    "QdrantServiceBackend",
    "SparseStoreBackend",
]
