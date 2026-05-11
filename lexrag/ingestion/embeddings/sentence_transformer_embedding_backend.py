"""Sentence-transformers backend for production embedding generation."""

from __future__ import annotations

from lexrag.ingestion.embeddings.embedding_backend import EmbeddingBackend
from lexrag.ingestion.embeddings.shared_model_registry import SharedModelRegistry


class SentenceTransformerEmbeddingBackend(EmbeddingBackend):
    """`sentence-transformers` backend with shared model loading."""

    def __init__(
        self,
        model_name: str,
        *,
        model_version: str = "local",
        local_files_only: bool = True,
        registry: SharedModelRegistry | None = None,
    ) -> None:
        self._registry = registry or SharedModelRegistry()
        self._model_name = model_name
        self._model_version = model_version
        self._model = self._registry.get_sentence_transformer(
            model_name=model_name,
            local_files_only=local_files_only,
        )
        dimension = self._model.get_embedding_dimension()
        if not dimension:
            raise RuntimeError("Unable to resolve embedding dimension from model")
        self._dimension = int(dimension)

    @property
    def dimension(self) -> int:
        """Return the vector dimension for the loaded model."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the configured sentence-transformers model name."""
        return self._model_name

    @property
    def model_version(self) -> str:
        """Return the configured model version string."""
        return self._model_version

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the cached sentence-transformers runtime."""
        vectors = self._model.encode(
            texts,
            batch_size=max(1, len(texts)),
            show_progress_bar=False,
            convert_to_numpy=False,
            normalize_embeddings=False,
        )
        return [list(map(float, vector)) for vector in vectors]
