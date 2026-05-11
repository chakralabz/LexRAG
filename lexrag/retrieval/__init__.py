"""Production retrieval layer exports.

This package owns query-time retrieval concerns only:

- dense retrieval over vector indexes
- sparse retrieval over lexical indexes
- hybrid fusion across retrieval strategies
- deterministic query decomposition heuristics
- reranking of retrieved candidates

Index mutation stays in ``lexrag.indexing`` and generation stays in
``lexrag.generation``. The exports below preserve a developer-friendly public
surface while the implementation remains internally modular.
"""

from lexrag.retrieval.base import Retriever
from lexrag.retrieval.dense_retriever import DenseRetriever
from lexrag.retrieval.hybrid_retriever import HybridRetriever
from lexrag.retrieval.query_decomposer import QueryDecomposer
from lexrag.retrieval.reranker import TokenOverlapReranker
from lexrag.retrieval.reranker_base import Reranker
from lexrag.retrieval.schemas import (
    DenseRetrieverConfig,
    HybridRetrieverConfig,
    QueryDecomposerConfig,
    RetrievalHit,
    SparseRetrieverConfig,
    TokenOverlapRerankerConfig,
)
from lexrag.retrieval.sparse_retriever import SparseRetriever

__all__ = [
    "DenseRetriever",
    "DenseRetrieverConfig",
    "HybridRetriever",
    "HybridRetrieverConfig",
    "QueryDecomposer",
    "QueryDecomposerConfig",
    "Reranker",
    "RetrievalHit",
    "Retriever",
    "SparseRetriever",
    "SparseRetrieverConfig",
    "TokenOverlapReranker",
    "TokenOverlapRerankerConfig",
]
