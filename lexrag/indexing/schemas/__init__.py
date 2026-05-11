"""Schema exports for the indexing layer.

The indexing package depends on canonical chunk contracts from the chunking
layer and adds only the schemas that are truly owned by storage and evaluation.
Keeping these contracts in one package keeps imports stable and prevents store
backends from importing orchestration code.
"""

from __future__ import annotations

from lexrag.indexing.schemas.qa_pair import QAPair
from lexrag.indexing.schemas.sparse_index_config import SparseIndexConfig
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.vector.schemas.index_optimization_config import IndexOptimizationConfig
from lexrag.vector.schemas.index_optimization_report import IndexOptimizationReport
from lexrag.vector.schemas.vector_index_config import VectorIndexConfig as DenseIndexConfig
from lexrag.vector.schemas.vector_upsert_report import VectorUpsertReport

__all__ = [
    "Chunk",
    "ChunkMetadata",
    "DenseIndexConfig",
    "IndexOptimizationConfig",
    "IndexOptimizationReport",
    "QAPair",
    "SparseIndexConfig",
    "VectorUpsertReport",
]
