"""Schema exports for the vector lifecycle package."""

from __future__ import annotations

from lexrag.vector.schemas.index_optimization_config import (
    IndexOptimizationConfig,
)
from lexrag.vector.schemas.index_optimization_report import (
    IndexOptimizationReport,
)
from lexrag.vector.schemas.reindex_plan import ReindexPlan
from lexrag.vector.schemas.vector_deduplication_config import (
    VectorDeduplicationConfig,
)
from lexrag.vector.schemas.vector_deduplication_decision import (
    VectorDeduplicationDecision,
)
from lexrag.vector.schemas.vector_deduplication_report import (
    VectorDeduplicationReport,
)
from lexrag.vector.schemas.vector_index_config import VectorIndexConfig
from lexrag.vector.schemas.vector_upsert_report import VectorUpsertReport

__all__ = [
    "IndexOptimizationConfig",
    "IndexOptimizationReport",
    "ReindexPlan",
    "VectorDeduplicationConfig",
    "VectorDeduplicationDecision",
    "VectorDeduplicationReport",
    "VectorIndexConfig",
    "VectorUpsertReport",
]
