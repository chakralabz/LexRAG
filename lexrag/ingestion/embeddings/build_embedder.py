"""Factory helpers for embedding generator construction."""

from __future__ import annotations

from lexrag.config import get_settings
from lexrag.ingestion.embeddings.deterministic_hash_embedding_backend import (
    DeterministicHashEmbeddingBackend,
)
from lexrag.ingestion.embeddings.embedding_backend import EmbeddingBackend
from lexrag.ingestion.embeddings.embedding_generator import EmbeddingGenerator
from lexrag.ingestion.embeddings.embedding_mode import EmbeddingMode
from lexrag.ingestion.embeddings.schemas.embedding_generation_config import (
    EmbeddingGenerationConfig,
)
from lexrag.ingestion.embeddings.sentence_transformer_embedding_backend import (
    SentenceTransformerEmbeddingBackend,
)
from lexrag.ingestion.embeddings.shared_model_registry import SharedModelRegistry


def build_embedder(
    *,
    mode: EmbeddingMode | str = EmbeddingMode.PRODUCTION,
    registry: SharedModelRegistry | None = None,
) -> EmbeddingGenerator:
    """Build the default embedding generator for the requested mode."""
    resolved_mode = EmbeddingMode(mode)
    shared_registry = registry or SharedModelRegistry()
    if resolved_mode is EmbeddingMode.DETERMINISTIC_TEST_ONLY:
        backend: EmbeddingBackend = DeterministicHashEmbeddingBackend()
        config = EmbeddingGenerationConfig(
            model_name=backend.model_name,
            model_version=backend.model_version,
            expected_dimension=backend.dimension,
        )
        return EmbeddingGenerator(config=config, backend=backend)
    settings = get_settings()
    backend = SentenceTransformerEmbeddingBackend(
        model_name=settings.EMBED_MODEL,
        registry=shared_registry,
    )
    config = EmbeddingGenerationConfig(
        model_name=settings.EMBED_MODEL,
        batch_size=settings.EMBED_BATCH_SIZE,
        expected_dimension=backend.dimension,
    )
    return EmbeddingGenerator(config=config, backend=backend)
