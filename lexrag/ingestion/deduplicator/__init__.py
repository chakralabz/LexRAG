"""Public API for deduplication across lexical and vector stages."""

from lexrag.ingestion.deduplicator.block_deduplicator import BlockDeduplicator
from lexrag.ingestion.deduplicator.deduplication_stats import DeduplicationStats
from lexrag.ingestion.deduplicator.deduplicator_base import Deduplicator
from lexrag.ingestion.deduplicator.min_hash_deduplicator import MinHashDeduplicator
from lexrag.ingestion.deduplicator.schemas import (
    BlockDeduplicationConfig,
    BlockDeduplicationDecision,
    DeduplicationRunReport,
    VectorDeduplicationConfig,
    VectorDeduplicationDecision,
    VectorDeduplicationReport,
)
from lexrag.ingestion.deduplicator.similarity_engine import SimilarityEngine
from lexrag.vector.vector_deduplicator import VectorDeduplicator
from lexrag.vector.vector_similarity_engine import VectorSimilarityEngine

__all__ = [
    "BlockDeduplicationConfig",
    "BlockDeduplicationDecision",
    "BlockDeduplicator",
    "DeduplicationRunReport",
    "DeduplicationStats",
    "Deduplicator",
    "MinHashDeduplicator",
    "SimilarityEngine",
    "VectorDeduplicationConfig",
    "VectorDeduplicationDecision",
    "VectorDeduplicationReport",
    "VectorDeduplicator",
    "VectorSimilarityEngine",
]
