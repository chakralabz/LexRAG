"""Shared registry for embedding models and tokenizers."""

from __future__ import annotations

from threading import RLock
from typing import Any

from lexrag.ingestion.chunker.whitespace_tokenizer import WhitespaceTokenizer


class SharedModelRegistry:
    """Cache tokenizer and embedding model artifacts process-wide."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tokenizers: dict[tuple[str, bool], Any] = {}
        self._sentence_transformers: dict[tuple[str, bool], Any] = {}

    def get_tokenizer(self, *, model_name: str, local_files_only: bool) -> Any:
        """Return one cached tokenizer instance for the given model."""
        cache_key = (model_name, local_files_only)
        with self._lock:
            tokenizer = self._tokenizers.get(cache_key)
            if tokenizer is None:
                tokenizer = self._load_tokenizer(
                    model_name=model_name,
                    local_files_only=local_files_only,
                )
                self._tokenizers[cache_key] = tokenizer
            return tokenizer

    def get_sentence_transformer(
        self,
        *,
        model_name: str,
        local_files_only: bool,
    ) -> Any:
        """Return one cached sentence-transformer instance for the model."""
        cache_key = (model_name, local_files_only)
        with self._lock:
            model = self._sentence_transformers.get(cache_key)
            if model is None:
                model = self._load_sentence_transformer(
                    model_name=model_name,
                    local_files_only=local_files_only,
                )
                self._sentence_transformers[cache_key] = model
            return model

    def _load_tokenizer(self, *, model_name: str, local_files_only: bool) -> Any:
        """Load one tokenizer, falling back to whitespace tokenization."""
        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                use_fast=True,
                local_files_only=local_files_only,
            )
        except Exception:
            return WhitespaceTokenizer()
        if tokenizer.is_fast is not True:
            raise RuntimeError(
                f"Tokenizer for model '{model_name}' is not a fast tokenizer"
            )
        return tokenizer

    def _load_sentence_transformer(
        self,
        *,
        model_name: str,
        local_files_only: bool,
    ) -> Any:
        """Load one sentence-transformers model instance."""
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("sentence-transformers is not installed") from exc
        return SentenceTransformer(model_name, local_files_only=local_files_only)
