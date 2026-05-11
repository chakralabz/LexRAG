"""Public embedding service with explicit model lifecycle management."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.embeddings.build_embedder import build_embedder
from lexrag.ingestion.embeddings.embedding_generator import EmbeddingGenerator
from lexrag.ingestion.embeddings.embedding_mode import EmbeddingMode
from lexrag.runtime import ManagedResource


class EmbeddingService:
    """Load and reuse embedding runtimes across multiple requests."""

    def __init__(
        self,
        *,
        generator_factory: Callable[[], EmbeddingGenerator] | None = None,
        finalizer: Callable[[EmbeddingGenerator], None] | None = None,
    ) -> None:
        factory = generator_factory or _build_embedding_generator
        self._resource = ManagedResource(loader=factory, finalizer=finalizer)

    @property
    def loaded(self) -> bool:
        """Return whether the embedding runtime has been initialized."""
        return self._resource.loaded

    def load(self) -> EmbeddingService:
        """Initialize the embedding runtime and return this service."""
        self._resource.load()
        return self

    def close(self) -> None:
        """Release the cached embedding runtime."""
        self._resource.close()

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        """Embed raw texts using the managed embedding runtime."""
        generator = self._resource.get()
        return generator.embed_texts(texts)

    def embed_query(self, query: str) -> list[float]:
        """Embed one retrieval query."""
        generator = self._resource.get()
        return generator.embed_query(query)

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Prepare and embed canonical chunks."""
        generator = self._resource.get()
        return generator.embed_chunks(chunks)

    def embed_prepared_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Embed chunks that already contain prepared embedding text."""
        generator = self._resource.get()
        texts = [chunk.embedding_text or chunk.text for chunk in chunks]
        vectors = generator.embed_texts(texts)
        return self._attach_vectors(chunks=chunks, vectors=vectors, generator=generator)

    def _attach_vectors(
        self,
        *,
        chunks: list[Chunk],
        vectors: list[list[float]],
        generator: EmbeddingGenerator,
    ) -> list[Chunk]:
        embedded: list[Chunk] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            metadata = chunk.metadata.model_copy(
                update={
                    "embedding_model": generator.backend.model_name,
                    "embedding_model_version": generator.backend.model_version,
                }
            )
            embedded.append(
                chunk.model_copy(update={"embedding": vector, "metadata": metadata})
            )
        return embedded


def _build_embedding_generator() -> EmbeddingGenerator:
    """Build the default production embedding runtime."""
    return build_embedder(mode=EmbeddingMode.PRODUCTION)
