"""Embedding preparation orchestration for canonical chunks."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.tokenization_engine import TokenizationEngine
from lexrag.ingestion.embeddings.embedding_text_builder import EmbeddingTextBuilder
from lexrag.ingestion.embeddings.schemas.embedding_preparation_config import (
    EmbeddingPreparationConfig,
)


class EmbeddingPreparationService:
    """Prepare canonical chunks for embedding generation."""

    def __init__(
        self,
        *,
        config: EmbeddingPreparationConfig | None = None,
        builder: EmbeddingTextBuilder | None = None,
        tokenization_engine: TokenizationEngine | None = None,
    ) -> None:
        self.config = config or EmbeddingPreparationConfig()
        self.builder = builder or EmbeddingTextBuilder(config=self.config)
        self.tokenization_engine = tokenization_engine or TokenizationEngine()

    def prepare_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Prepare many chunks for embedding generation."""
        return [self.prepare_chunk(chunk=chunk) for chunk in chunks]

    def prepare_chunk(self, *, chunk: Chunk) -> Chunk:
        """Prepare one chunk for embedding generation."""
        embedding_text = self.builder.build(chunk=chunk)
        embedding_text, truncated = self._validated_text(embedding_text=embedding_text)
        metadata = dict(chunk.metadata.metadata)
        metadata["embedding_text_truncated"] = truncated
        metadata["embedding_text_token_count"] = self.tokenization_engine.count_tokens(
            embedding_text
        )
        return chunk.model_copy(
            update={
                "embedding_text": embedding_text,
                "metadata": chunk.metadata.model_copy(update={"metadata": metadata}),
            }
        )

    def _validated_text(self, *, embedding_text: str) -> tuple[str, bool]:
        """Validate embedding text against the configured model budget."""
        tokens = self.tokenization_engine.tokenize(embedding_text)
        if len(tokens) <= self.config.max_embedding_tokens:
            return embedding_text.strip(), False
        if not self.config.truncate_over_budget:
            raise ValueError("embedding text exceeds configured token budget")
        trimmed = tokens[: self.config.max_embedding_tokens]
        return self.tokenization_engine.detokenize(trimmed).strip(), True
