"""Utilities for warming embedding artifacts before request traffic."""

from __future__ import annotations

from lexrag.ingestion.embeddings.shared_model_registry import SharedModelRegistry


class EmbeddingModelPreloader:
    """Warm embedding-related artifacts ahead of runtime traffic."""

    def __init__(self, *, registry: SharedModelRegistry | None = None) -> None:
        self.registry = registry or SharedModelRegistry()

    def preload_tokenizer(self, *, model_name: str, allow_download: bool) -> object:
        """Resolve and cache the tokenizer for the target embedding model."""
        return self.registry.get_tokenizer(
            model_name=model_name,
            local_files_only=not allow_download,
        )

    def preload_sentence_transformer(
        self,
        *,
        model_name: str,
        allow_download: bool,
    ) -> object:
        """Resolve and cache the sentence-transformer for the target model."""
        return self.registry.get_sentence_transformer(
            model_name=model_name,
            local_files_only=not allow_download,
        )

    def preload_embedding_stack(
        self,
        *,
        model_name: str,
        allow_download: bool = False,
    ) -> None:
        """Warm both tokenizer and embedding model for one embedding stack."""
        self.preload_tokenizer(model_name=model_name, allow_download=allow_download)
        self.preload_sentence_transformer(
            model_name=model_name,
            allow_download=allow_download,
        )
