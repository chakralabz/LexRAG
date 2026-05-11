"""Vector lifecycle package for deduplication, upserts, and index tuning.

This package owns the post-embedding lifecycle described in
`docs/architecture.md`:

- vector-level semantic deduplication
- version-aware vector database upserts
- backend optimization policy
- deterministic re-index planning

The goal is to keep storage adapters in `lexrag.indexing.backends` thin while
concentrating production policy in one import-safe boundary.
"""

from __future__ import annotations

from lexrag.vector.index_optimizer import IndexOptimizer
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.vector.schemas import (
    IndexOptimizationConfig,
    IndexOptimizationReport,
    ReindexPlan,
    VectorDeduplicationConfig,
    VectorDeduplicationDecision,
    VectorDeduplicationReport,
    VectorIndexConfig,
    VectorUpsertReport,
)
from lexrag.vector.vector_deduplicator import VectorDeduplicator
from lexrag.vector.vector_similarity_engine import VectorSimilarityEngine

__all__ = [
    "IndexOptimizationConfig",
    "IndexOptimizationReport",
    "IndexOptimizer",
    "QdrantStore",
    "ReindexPlan",
    "VectorDeduplicationConfig",
    "VectorDeduplicationDecision",
    "VectorDeduplicationReport",
    "VectorDeduplicator",
    "VectorIndexConfig",
    "VectorSimilarityEngine",
    "VectorUpsertReport",
]
