"""Index optimization service for dense and sparse stores."""

from __future__ import annotations

from lexrag.indexing.backends.dense_store_backend import DenseStoreBackend
from lexrag.indexing.backends.sparse_store_backend import SparseStoreBackend
from lexrag.vector.schemas import IndexOptimizationConfig, IndexOptimizationReport


class IndexOptimizer:
    """Applies architecture-mandated index tuning in one place.

    Store facades own write semantics and version policy. This service owns the
    declarative optimization rules that make metadata filters and retrieval
    latency predictable across storage backends.
    """

    def __init__(self, *, config: IndexOptimizationConfig | None = None) -> None:
        self.config = config or IndexOptimizationConfig()

    def optimize_dense(self, *, backend: DenseStoreBackend) -> IndexOptimizationReport:
        """Ensure dense backend metadata indexes exist."""

        metadata_indexes = backend.ensure_metadata_indexes(
            list(self.config.filterable_metadata_fields)
        )
        return IndexOptimizationReport(
            backend_name=backend.__class__.__name__,
            dense_algorithm=self.config.dense_algorithm,
            metadata_indexes=metadata_indexes,
        )

    def optimize_sparse(
        self,
        *,
        backend: SparseStoreBackend,
    ) -> IndexOptimizationReport:
        """Ensure sparse backend metadata indexes exist."""

        metadata_indexes = backend.ensure_metadata_indexes(
            list(self.config.filterable_metadata_fields)
        )
        return IndexOptimizationReport(
            backend_name=backend.__class__.__name__,
            sparse_strategy=self.config.sparse_strategy,
            metadata_indexes=metadata_indexes,
        )
