"""Load validated SDK configuration from YAML, environment, and overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from lexrag.config.package_settings import LexRAGSettings

_YAML_PATHS: dict[str, tuple[str, ...]] = {
    "log_level": ("logging", "level"),
    "log_format": ("logging", "format"),
    "embed_model": ("models", "embed_model"),
    "rerank_model": ("models", "rerank_model"),
    "qdrant_url": ("infra", "qdrant_url"),
    "qdrant_collection": ("infra", "qdrant_collection"),
    "elasticsearch_url": ("infra", "elasticsearch_url"),
    "elasticsearch_index": ("infra", "elasticsearch_index"),
    "embed_batch_size": ("ingestion", "embed_batch_size"),
    "min_chunk_tokens": ("ingestion", "min_chunk_tokens"),
    "max_chunk_tokens": ("ingestion", "max_chunk_tokens"),
    "semantic_chunk_threshold": ("ingestion", "semantic_chunk_threshold"),
    "retrieval_top_k": ("retrieval", "rerank_top_k"),
    "retriever_top_n": ("retrieval", "top_n"),
}

_ENV_MAP: dict[str, str] = {
    "environment": "LEXRAG_ENV",
    "log_level": "LEXRAG_LOG_LEVEL",
    "log_format": "LEXRAG_LOG_FORMAT",
    "embed_model": "EMBED_MODEL",
    "rerank_model": "RERANK_MODEL",
    "qdrant_url": "QDRANT_URL",
    "qdrant_collection": "QDRANT_COLLECTION",
    "elasticsearch_url": "ELASTICSEARCH_URL",
    "elasticsearch_index": "ELASTICSEARCH_INDEX",
    "embed_batch_size": "EMBED_BATCH_SIZE",
    "min_chunk_tokens": "MIN_CHUNK_TOKENS",
    "max_chunk_tokens": "MAX_CHUNK_TOKENS",
    "semantic_chunk_threshold": "SEMANTIC_CHUNK_THRESHOLD",
    "retrieval_top_k": "RERANK_TOP_K",
    "retriever_top_n": "RETRIEVAL_TOP_N",
}


class ConfigLoader:
    """Assemble package settings from deterministic configuration sources."""

    def __init__(self, *, default_path: Path | None = None) -> None:
        self._default_path = default_path or Path("config.yaml")

    def load(
        self,
        *,
        config_path: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> LexRAGSettings:
        """Load settings with YAML < ENV < explicit override precedence."""
        path = Path(config_path) if config_path is not None else self._default_path
        payload = self._yaml_payload(path=path)
        payload.update(self._env_payload())
        payload.update(overrides or {})
        payload["config_path"] = path if path.exists() else None
        return LexRAGSettings.model_validate(payload)

    def _yaml_payload(self, *, path: Path) -> dict[str, Any]:
        """Read supported settings from an optional YAML file."""
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        payload = {field: _yaml_get(data, keys) for field, keys in _YAML_PATHS.items()}
        return {field: value for field, value in payload.items() if value is not None}

    def _env_payload(self) -> dict[str, Any]:
        """Read supported settings from environment variables."""
        payload: dict[str, Any] = {}
        for field, env_name in _ENV_MAP.items():
            value = os.getenv(env_name)
            if value is not None:
                payload[field] = value
        return payload


def _yaml_get(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Resolve one nested YAML field into a flat settings value."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current
