"""Schemas owned by the retrieval layer.

Keeping configs and query-time DTOs in a dedicated schema package prevents
retrievers from depending on one another's implementation details and keeps
imports stable for callers in eval, serving, and future API layers.
"""

from lexrag.retrieval.schemas.dense_retriever_config import DenseRetrieverConfig
from lexrag.retrieval.schemas.hybrid_retriever_config import HybridRetrieverConfig
from lexrag.retrieval.schemas.query_decomposer_config import QueryDecomposerConfig
from lexrag.retrieval.schemas.retrieval_hit import RetrievalHit
from lexrag.retrieval.schemas.sparse_retriever_config import SparseRetrieverConfig
from lexrag.retrieval.schemas.token_overlap_reranker_config import (
    TokenOverlapRerankerConfig,
)

__all__ = [
    "DenseRetrieverConfig",
    "HybridRetrieverConfig",
    "QueryDecomposerConfig",
    "RetrievalHit",
    "SparseRetrieverConfig",
    "TokenOverlapRerankerConfig",
]
