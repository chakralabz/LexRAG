"""Abstract contract for dense vector storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk


class DenseStoreBackend(ABC):
    """Define the minimum behavior required by dense storage adapters."""

    @abstractmethod
    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Write chunks into backend storage."""

    @abstractmethod
    def search_dense(
        self,
        query_vector: list[float],
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None,
    ) -> list[Chunk]:
        """Run dense vector search with optional metadata filtering."""

    @abstractmethod
    def list_chunks(
        self,
        *,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Return stored chunks matching metadata filters."""

    @abstractmethod
    def delete_chunks(self, chunk_ids: list[str]) -> int:
        """Delete the supplied chunk IDs from backend storage."""

    @abstractmethod
    def delete_collection(self) -> None:
        """Delete all data associated with the active collection."""

    @abstractmethod
    def count(self) -> int:
        """Return indexed chunk count."""

    @abstractmethod
    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        """Ensure metadata filter indexes exist and return realized fields."""
