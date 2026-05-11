"""Backend protocol for embedding generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingBackend(ABC):
    """Abstract backend interface for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimension emitted by this backend."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the provider model identifier."""

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Return the pinned model version for metadata provenance."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts in one provider call."""
