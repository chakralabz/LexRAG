"""Abstract contract for sparse lexical storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lexrag.ingestion.chunker.schemas.chunk import Chunk


class SparseStoreBackend(ABC):
    """Define the minimum behavior required by sparse index adapters."""

    @abstractmethod
    def index_chunks(self, chunks: list[Chunk]) -> int:
        """Write chunks into sparse backend storage."""

    @abstractmethod
    def search_bm25(
        self,
        query: str,
        *,
        limit: int,
        metadata_filters: dict[str, Any] | None,
    ) -> list[Chunk]:
        """Run sparse keyword retrieval with optional filters."""

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
    def count(self) -> int:
        """Return indexed chunk count."""

    @abstractmethod
    def ensure_metadata_indexes(self, fields: list[str]) -> list[str]:
        """Ensure metadata filter indexes exist and return realized fields."""
