"""Architecture-owned catalog of monitoring metrics and alert thresholds."""

from __future__ import annotations

from typing import Literal

from lexrag.observability.schemas import AlertThreshold, MetricDefinition


class MonitoringCatalog:
    """Expose the monitoring contract documented in `docs/architecture.md`.

    Keeping the catalog in code prevents metrics from becoming tribal knowledge.
    Alerting, dashboards, and tests can all depend on the same typed registry
    instead of manually re-encoding metric names and thresholds.
    """

    def __init__(self) -> None:
        self._definitions = tuple(_default_definitions())

    def definitions(self) -> tuple[MetricDefinition, ...]:
        """Return the complete metric catalog."""
        return self._definitions

    def metric_names(self) -> set[str]:
        """Return all registered metric names."""
        return {definition.name for definition in self._definitions}

    def by_name(self, name: str) -> MetricDefinition:
        """Return the metric definition for a stable metric name."""
        for definition in self._definitions:
            if definition.name == name:
                return definition
        raise KeyError(f"Unknown monitoring metric: {name}")


def _default_definitions() -> list[MetricDefinition]:
    return [
        *_ingestion_metrics(),
        *_block_quality_metrics(),
        *_chunking_metrics(),
        *_embedding_metrics(),
        *_retrieval_metrics(),
        *_alert_metrics(),
    ]


def _ingestion_metrics() -> list[MetricDefinition]:
    return [
        _metric("parser_success_rate", "ingestion", "Docs parsed without fallback."),
        _metric("parser_fallback_rate", "ingestion", "Docs requiring fallback."),
        _metric("ocr_activation_rate", "ingestion", "Docs requiring OCR."),
        _metric("parse_confidence_p50", "ingestion", "Median parser confidence."),
        _metric("parse_confidence_p95", "ingestion", "P95 parser confidence."),
        _metric("file_type_failure_rate", "ingestion", "Failures by file type."),
        _metric("manual_recovery_rate", "ingestion", "Docs routed to manual recovery."),
    ]


def _block_quality_metrics() -> list[MetricDefinition]:
    return [
        _metric("block_drop_rate", "block_quality", "Blocks dropped by validation."),
        _metric("ocr_cleanup_rate", "block_quality", "Blocks changed by OCR repair."),
        _metric(
            "artifact_removal_rate",
            "block_quality",
            "Blocks cleaned for parser artifacts.",
        ),
        _metric("malformed_table_rate", "block_quality", "Tables requiring repair."),
        _metric("dedup_drop_rate", "block_quality", "Blocks removed by dedup."),
    ]


def _chunking_metrics() -> list[MetricDefinition]:
    return [
        _metric("avg_chunk_token_count", "chunking", "Average chunk token count."),
        _metric(
            "chunk_quality_score_p50",
            "chunking",
            "Median chunk quality score.",
        ),
        _metric("chunk_quality_score_p95", "chunking", "P95 chunk quality score."),
        _metric(
            "standalone_block_ratio",
            "chunking",
            "Share of standalone table/code chunks.",
        ),
        _metric(
            "overlap_validation_failures",
            "chunking",
            "Chunks with invalid overlap lineage.",
        ),
    ]


def _embedding_metrics() -> list[MetricDefinition]:
    return [
        _metric("embedding_failure_rate", "embedding", "Failed embeddings."),
        _metric("embedding_retry_rate", "embedding", "Embeddings requiring retry."),
        _metric("vector_duplicate_rate", "embedding", "Vectors suppressed by dedup."),
        _metric("upsert_failure_rate", "embedding", "Failed vector upserts."),
        _metric(
            "re_index_consistency_rate",
            "embedding",
            "Re-indexes with zero orphan chunks.",
        ),
    ]


def _retrieval_metrics() -> list[MetricDefinition]:
    return [
        _metric(
            "retrieval_hit_rate",
            "retrieval",
            "Queries returning at least one strong chunk.",
        ),
        _metric(
            "reranker_correction_rate",
            "retrieval",
            "Queries where reranker changed top-1.",
        ),
        _metric(
            "citation_success_rate",
            "retrieval",
            "Answers with all citations validated.",
        ),
        _metric(
            "orphan_citation_rate",
            "retrieval",
            "Cited IDs not found in context window.",
            warning=0.01,
            critical=0.05,
        ),
        _metric(
            "unsupported_answer_rate",
            "retrieval",
            "Answers that should have abstained.",
            warning=0.10,
            critical=0.25,
        ),
        _metric(
            "faithfulness_score_p50",
            "retrieval",
            "Median NLI faithfulness score.",
        ),
    ]


def _alert_metrics() -> list[MetricDefinition]:
    return [
        _metric(
            "chunk_quality_score_p50_alert",
            "alerts",
            "Derived alert for chunk quality score.",
            warning=0.60,
            critical=0.40,
            direction="below",
        ),
        _metric(
            "parser_fallback_rate_alert",
            "alerts",
            "Derived alert for parser fallbacks.",
            warning=0.15,
            critical=0.30,
        ),
        _metric(
            "manual_recovery_rate_alert",
            "alerts",
            "Derived alert for manual recovery.",
            warning=0.02,
            critical=0.05,
        ),
        _metric(
            "upsert_failure_rate_alert",
            "alerts",
            "Derived alert for vector upsert failures.",
            warning=0.005,
            critical=0.02,
        ),
    ]


def _metric(
    name: str,
    layer: str,
    description: str,
    *,
    warning: float | None = None,
    critical: float | None = None,
    direction: Literal["above", "below"] = "above",
) -> MetricDefinition:
    threshold = _threshold(
        warning=warning,
        critical=critical,
        direction=direction,
    )
    return MetricDefinition(
        name=name,
        layer=layer,
        description=description,
        alert_threshold=threshold,
    )


def _threshold(
    *,
    warning: float | None,
    critical: float | None,
    direction: Literal["above", "below"],
) -> AlertThreshold | None:
    if warning is None or critical is None:
        return None
    return AlertThreshold(
        warning=warning,
        critical=critical,
        direction=direction,
    )
