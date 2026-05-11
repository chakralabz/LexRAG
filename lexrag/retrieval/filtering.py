"""Metadata-filter helpers for retrieval-time evaluation.

The indexing backends currently support equality filters natively. Retrieval
owns richer query-time semantics such as ``in`` and comparison operators, so we
split incoming filters into:

- backend-safe equality filters delegated to storage
- residual filters evaluated against returned chunks

This design preserves clean package boundaries while still letting API callers
use a more expressive filter language.
"""

from __future__ import annotations

from typing import Any

from lexrag.indexing.schemas import Chunk

_FILTER_ALIASES = {
    "document_id": "doc_id",
    "document_type": "doc_type",
    "page": "page_start",
}
_COMPARISON_OPERATORS = {"eq", "in", "gt", "gte", "lt", "lte"}


def split_backend_filters(
    metadata_filters: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Split incoming filters into storage-safe and residual expressions.

    Args:
        metadata_filters: Caller-provided filter dictionary.

    Returns:
        A tuple of ``(backend_filters, residual_filters)`` where backend filters
        are simple equality checks safe to delegate to storage adapters.
    """

    if not metadata_filters:
        return {}, {}
    backend_filters: dict[str, Any] = {}
    residual_filters: dict[str, dict[str, Any]] = {}
    for raw_field, raw_value in metadata_filters.items():
        field = _normalize_field_name(raw_field)
        if isinstance(raw_value, dict):
            _assign_structured_filter(
                field=field,
                raw_value=raw_value,
                backend_filters=backend_filters,
                residual_filters=residual_filters,
            )
            continue
        backend_filters[field] = raw_value
    return backend_filters, residual_filters


def matches_residual_filters(
    chunk: Chunk,
    residual_filters: dict[str, dict[str, Any]],
) -> bool:
    """Return whether a chunk satisfies the non-backend-safe filter clauses."""

    if not residual_filters:
        return True
    for field, operations in residual_filters.items():
        value = _metadata_value(chunk=chunk, field=field)
        if not _matches_operations(value=value, operations=operations):
            return False
    return True


def _assign_structured_filter(
    *,
    field: str,
    raw_value: dict[str, Any],
    backend_filters: dict[str, Any],
    residual_filters: dict[str, dict[str, Any]],
) -> None:
    """Route one structured filter into backend or residual evaluation."""

    invalid = set(raw_value) - _COMPARISON_OPERATORS
    if invalid:
        raise ValueError(f"Unsupported filter operators for {field}: {sorted(invalid)}")
    if set(raw_value) == {"eq"}:
        backend_filters[field] = raw_value["eq"]
        return
    residual_filters[field] = raw_value


def _normalize_field_name(field: str) -> str:
    """Map API-facing aliases onto canonical chunk-metadata field names."""

    return _FILTER_ALIASES.get(field, field)


def _metadata_value(*, chunk: Chunk, field: str) -> Any:
    """Resolve a filter field from canonical metadata or free-form metadata."""

    payload = chunk.metadata.model_dump(mode="python")
    if field in payload:
        return payload[field]
    return chunk.metadata.metadata.get(field)


def _matches_operations(*, value: Any, operations: dict[str, Any]) -> bool:
    """Evaluate a normalized operator dictionary against one metadata value."""

    for operator, expected in operations.items():
        if operator == "in" and value not in expected:
            return False
        if operator == "eq" and value != expected:
            return False
        if operator == "gt" and not _compare(value=value, expected=expected, kind="gt"):
            return False
        if operator == "gte" and not _compare(
            value=value,
            expected=expected,
            kind="gte",
        ):
            return False
        if operator == "lt" and not _compare(value=value, expected=expected, kind="lt"):
            return False
        if operator == "lte" and not _compare(
            value=value,
            expected=expected,
            kind="lte",
        ):
            return False
    return True


def _compare(*, value: Any, expected: Any, kind: str) -> bool:
    """Compare scalar metadata values safely for ordering operators."""

    if value is None:
        return False
    if kind == "gt":
        return value > expected
    if kind == "gte":
        return value >= expected
    if kind == "lt":
        return value < expected
    return value <= expected
