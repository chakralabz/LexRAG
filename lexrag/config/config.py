"""Centralized configuration for LexRAG."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV = os.getenv("LEXRAG_ENV", "DEV").upper()

_FORBIDDEN_YAML_PATHS = [
    ("env", "name"),
    ("env", "use_real_stores"),
    ("infra", "qdrant_api_key"),
    ("observability", "langfuse_public_key"),
    ("observability", "langfuse_secret_key"),
    ("api", "secret_key"),
]

_YAML_FIELD_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("LEXRAG_LOG_LEVEL", ("logging", "level")),
    ("LEXRAG_LOG_FORMAT", ("logging", "format")),
    ("EMBED_MODEL", ("models", "embed_model")),
    ("RERANK_MODEL", ("models", "rerank_model")),
    ("NLI_MODEL", ("models", "nli_model")),
    ("LLM_MODEL", ("models", "llm_model")),
    ("QDRANT_URL", ("infra", "qdrant_url")),
    ("QDRANT_COLLECTION", ("infra", "qdrant_collection")),
    ("ELASTICSEARCH_URL", ("infra", "elasticsearch_url")),
    ("ELASTICSEARCH_INDEX", ("infra", "elasticsearch_index")),
    ("REDIS_URL", ("infra", "redis_url")),
    ("LANGFUSE_HOST", ("observability", "langfuse_host")),
    ("RETRIEVAL_ALPHA", ("retrieval", "alpha")),
    ("RERANK_TOP_K", ("retrieval", "rerank_top_k")),
    ("RETRIEVAL_TOP_N", ("retrieval", "top_n")),
    ("MIN_CHUNK_TOKENS", ("ingestion", "min_chunk_tokens")),
    ("MAX_CHUNK_TOKENS", ("ingestion", "max_chunk_tokens")),
    ("SEMANTIC_CHUNK_THRESHOLD", ("ingestion", "semantic_chunk_threshold")),
    ("EMBED_BATCH_SIZE", ("ingestion", "embed_batch_size")),
    ("OCR_REJECT_THRESHOLD", ("ingestion", "ocr_reject_threshold")),
    ("OCR_ABSTAIN_THRESHOLD", ("ingestion", "ocr_abstain_threshold")),
    (
        "FAITHFULNESS_CONTRADICTION_THRESHOLD",
        ("generation", "faithfulness_contradiction_threshold"),
    ),
    (
        "FAITHFULNESS_NEUTRAL_RATIO_THRESHOLD",
        ("generation", "faithfulness_neutral_ratio_threshold"),
    ),
    ("CACHE_SIMILARITY_THRESHOLD", ("cache", "similarity_threshold")),
    ("CACHE_TTL_SECONDS", ("cache", "ttl_seconds")),
    ("LEXRAG_ENABLE_HTTP_INGEST", ("api", "enable_http_ingest")),
    ("RATE_LIMIT_PER_MINUTE", ("api", "rate_limit_per_minute")),
    ("INGEST_INPUT_DIR", ("paths", "ingest_input_dir")),
    ("EVAL_DATASET_PATH", ("paths", "eval_dataset_path")),
    ("EVAL_RESULTS_DIR", ("paths", "eval_results_dir")),
    ("TESTCASE_DATASET_PATH", ("paths", "testcase_dataset_path")),
    ("TESTCASE_RESULTS_DIR", ("paths", "testcase_results_dir")),
)


def load_yaml() -> dict[str, Any]:
    """Loads optional low-priority config from `config.yaml`."""
    path = BASE_DIR / "config.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _yaml_get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _validate_yaml_policy(yaml_data: dict[str, Any]) -> None:
    violations = [
        ".".join(path)
        for path in _FORBIDDEN_YAML_PATHS
        if _yaml_get(yaml_data, *path) is not None
    ]
    if violations:
        joined = ", ".join(violations)
        raise ValueError(
            f"Forbidden keys found in config.yaml (must be in env/.env): {joined}"
        )


def _yaml_field_values(yaml_data: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_name, path in _YAML_FIELD_PATHS:
        value = _yaml_get(yaml_data, *path)
        if value is not None:
            values[field_name] = value
    return values


def _resolve_yaml_overrides(
    settings: Settings, yaml_data: dict[str, Any]
) -> dict[str, Any]:
    yaml_values = _yaml_field_values(yaml_data)
    overrides: dict[str, Any] = {}
    for field_name, value in yaml_values.items():
        env_override = os.getenv(field_name)
        if env_override is not None:
            continue
        default = Settings.model_fields[field_name].default
        current = getattr(settings, field_name)
        if current == default:
            overrides[field_name] = value
    return overrides


def _apply_yaml_fallback(settings: Settings, yaml_data: dict[str, Any]) -> Settings:
    overrides = _resolve_yaml_overrides(settings, yaml_data)
    if not overrides:
        return settings
    payload = settings.model_dump()
    payload.update(overrides)
    return Settings.model_validate(payload)


class Settings(BaseSettings):
    """Typed runtime settings for ingestion, retrieval, serving, and eval."""

    LEXRAG_ENV: Literal["DEV", "PROD", "TEST"] = Field(default="DEV")
    LEXRAG_USE_REAL_STORES: bool = Field(default=False)
    LEXRAG_LOG_LEVEL: str = Field(default="INFO")
    LEXRAG_LOG_FORMAT: Literal["text", "json"] = Field(default="text")

    EMBED_MODEL: str = Field(default="BAAI/bge-m3")
    RERANK_MODEL: str = Field(default="cross-encoder/ms-marco-MiniLM-L-12-v2")
    NLI_MODEL: str = Field(default="cross-encoder/nli-deberta-v3-base")
    LLM_MODEL: str = Field(default="Qwen/Qwen2.5-7B-Instruct")

    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str | None = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="lexrag_chunks")
    ELASTICSEARCH_URL: str = Field(default="http://localhost:9200")
    ELASTICSEARCH_INDEX: str = Field(default="lexrag_chunks")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    LANGFUSE_PUBLIC_KEY: str | None = Field(default=None)
    LANGFUSE_SECRET_KEY: str | None = Field(default=None)
    LANGFUSE_HOST: str = Field(default="http://localhost:3001")

    RETRIEVAL_ALPHA: float = Field(default=0.5, ge=0.0, le=1.0)
    RERANK_TOP_K: int = Field(default=5, ge=1)
    RETRIEVAL_TOP_N: int = Field(default=20, ge=1)
    MIN_CHUNK_TOKENS: int = Field(default=128, ge=1)
    MAX_CHUNK_TOKENS: int = Field(default=512, ge=1)
    SEMANTIC_CHUNK_THRESHOLD: float = Field(default=0.75, ge=0.0, le=1.0)
    EMBED_BATCH_SIZE: int = Field(default=32, ge=1)
    OCR_REJECT_THRESHOLD: float = Field(default=0.20, ge=0.0, le=1.0)
    OCR_ABSTAIN_THRESHOLD: float = Field(default=0.50, ge=0.0, le=1.0)

    FAITHFULNESS_CONTRADICTION_THRESHOLD: float = Field(default=0.5, ge=0.0, le=1.0)
    FAITHFULNESS_NEUTRAL_RATIO_THRESHOLD: float = Field(default=0.3, ge=0.0, le=1.0)

    CACHE_SIMILARITY_THRESHOLD: float = Field(default=0.9, ge=0.0, le=1.0)
    CACHE_TTL_SECONDS: int = Field(default=3600, ge=1)
    API_SECRET_KEY: str | None = Field(default=None)
    LEXRAG_ENABLE_HTTP_INGEST: bool = Field(default=False)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=1)

    INGEST_INPUT_DIR: str = Field(default="data/arxiv/raw")
    EVAL_DATASET_PATH: str = Field(default="data/arxiv/qa_pairs.json")
    EVAL_RESULTS_DIR: str = Field(default="eval/results")
    TESTCASE_DATASET_PATH: str = Field(default="data/arxiv/testcases/qa_pairs_ci.json")
    TESTCASE_RESULTS_DIR: str = Field(default="eval/testcase_results")

    yaml_config: dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env" if ENV == "DEV" else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def _build_settings() -> Settings:
    yaml_data = load_yaml()
    _validate_yaml_policy(yaml_data)
    settings = Settings()
    settings = _apply_yaml_fallback(settings, yaml_data)
    _validate_runtime_security(settings)
    return settings.model_copy(update={"yaml_config": yaml_data})


def _validate_runtime_security(settings: Settings) -> None:
    """Reject insecure runtime defaults in production environments."""
    if settings.LEXRAG_ENV != "PROD":
        return
    if settings.API_SECRET_KEY:
        return
    raise ValueError("API_SECRET_KEY must be set when LEXRAG_ENV=PROD")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns process-wide cached settings instance."""
    return _build_settings()
