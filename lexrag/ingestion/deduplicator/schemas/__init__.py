"""Public schemas for the block-level deduplication package."""

from lexrag.ingestion.deduplicator.schemas.block_deduplication_config import (
    BlockDeduplicationConfig,
)
from lexrag.ingestion.deduplicator.schemas.block_deduplication_decision import (
    BlockDeduplicationDecision,
)
from lexrag.ingestion.deduplicator.schemas.deduplication_run_report import (
    DeduplicationRunReport,
)
from lexrag.vector.schemas import (
    VectorDeduplicationConfig,
    VectorDeduplicationDecision,
    VectorDeduplicationReport,
)

__all__ = [
    "BlockDeduplicationConfig",
    "BlockDeduplicationDecision",
    "DeduplicationRunReport",
    "VectorDeduplicationConfig",
    "VectorDeduplicationDecision",
    "VectorDeduplicationReport",
]
