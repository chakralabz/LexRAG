"""Validation service for chunk-level audit completeness."""

from __future__ import annotations

from collections.abc import Sequence

from lexrag.audit.schemas import (
    AuditRequirement,
    AuditValidationIssue,
    AuditValidationResult,
)
from lexrag.ingestion.chunker.schemas.chunk import Chunk


class ChunkAuditValidator:
    """Validate chunk metadata against the architecture's audit contract.

    The architecture document defines auditability as a product contract, not a
    best-effort hint. This validator centralizes that contract so ingestion,
    indexing, eval, and review tooling can all reason about missing metadata in
    exactly the same way.
    """

    def __init__(self, requirements: Sequence[AuditRequirement] | None = None) -> None:
        self._requirements = tuple(requirements or _default_requirements())

    def validate_chunk(self, chunk: Chunk) -> AuditValidationResult:
        """Return the audit completeness result for one chunk."""
        issues = self._collect_issues(chunk=chunk)
        score = self._completeness_score(issues=issues)
        return AuditValidationResult(
            subject_id=chunk.chunk_id,
            passed=not issues,
            completeness_score=score,
            issues=issues,
        )

    def validate_chunks(self, chunks: Sequence[Chunk]) -> list[AuditValidationResult]:
        """Validate an ordered chunk collection."""
        return [self.validate_chunk(chunk) for chunk in chunks]

    def auditability_score(self, chunks: Sequence[Chunk]) -> float:
        """Return the mean completeness score across a chunk collection."""
        results = self.validate_chunks(chunks)
        if not results:
            return 0.0
        total = sum(result.completeness_score for result in results)
        return total / len(results)

    def low_auditability_chunk_ids(
        self,
        chunks: Sequence[Chunk],
        *,
        threshold: float = 0.8,
    ) -> list[str]:
        """Return chunk IDs that fall below the configured audit threshold."""
        results = self.validate_chunks(chunks)
        return [
            result.subject_id
            for result in results
            if result.completeness_score < threshold
        ]

    def _collect_issues(self, *, chunk: Chunk) -> list[AuditValidationIssue]:
        issues: list[AuditValidationIssue] = []
        for requirement in self._requirements:
            if self._has_value(chunk=chunk, requirement=requirement):
                continue
            issues.append(self._missing_issue(chunk=chunk, requirement=requirement))
        return issues

    def _has_value(self, *, chunk: Chunk, requirement: AuditRequirement) -> bool:
        metadata = chunk.metadata
        for field_name in requirement.field_names:
            value = getattr(metadata, field_name, None)
            if _is_present(value):
                return True
        return False

    def _missing_issue(
        self,
        *,
        chunk: Chunk,
        requirement: AuditRequirement,
    ) -> AuditValidationIssue:
        return AuditValidationIssue(
            subject_id=chunk.chunk_id,
            field_name=requirement.primary_field_name,
            owner=requirement.owner,
            reason=(
                "Missing architecture-required audit metadata needed for "
                "traceability and operational review."
            ),
        )

    def _completeness_score(self, issues: Sequence[AuditValidationIssue]) -> float:
        total_requirements = max(len(self._requirements), 1)
        satisfied = total_requirements - len(issues)
        return satisfied / total_requirements


def _default_requirements() -> tuple[AuditRequirement, ...]:
    return (
        *_parser_requirements(),
        *_chunker_requirements(),
        *_pipeline_requirements(),
        *_embedding_requirements(),
    )


def _parser_requirements() -> tuple[AuditRequirement, ...]:
    return (
        _requirement("parser_used", owner="parser", description="Parser provenance."),
        _requirement("fallback_used", owner="parser", description="Fallback usage."),
        _requirement("ocr_used", owner="parser", description="OCR usage."),
        _requirement(
            "parse_confidence",
            owner="parser",
            description="Parser confidence score.",
        ),
    )


def _chunker_requirements() -> tuple[AuditRequirement, ...]:
    return (
        _requirement(
            "chunking_strategy",
            owner="chunker",
            description="Chunking strategy label.",
        ),
        _requirement(
            "heading_anchor",
            owner="normalizer",
            description="Stable heading anchor.",
        ),
        _requirement(
            "overlap_prev",
            "previous_chunk_id",
            owner="chunker",
            description="Backward overlap lineage.",
        ),
        _requirement(
            "overlap_next",
            "next_chunk_id",
            owner="chunker",
            description="Forward overlap lineage.",
        ),
        _requirement(
            "source_block_ids",
            owner="chunker",
            description="Source block lineage.",
        ),
        _requirement(
            "chunk_quality_score",
            owner="chunk_post_processor",
            description="Chunk quality score.",
        ),
    )


def _pipeline_requirements() -> tuple[AuditRequirement, ...]:
    return (
        _requirement(
            "ingestion_timestamp",
            owner="ingestion_pipeline",
            description="UTC ingestion timestamp.",
        ),
        _requirement(
            "document_version",
            owner="metadata_store",
            description="Document version label.",
        ),
    )


def _embedding_requirements() -> tuple[AuditRequirement, ...]:
    return (
        _requirement(
            "embedding_model",
            owner="embedding",
            description="Embedding model name.",
        ),
        _requirement(
            "embedding_model_version",
            owner="embedding",
            description="Embedding model version.",
        ),
    )


def _requirement(
    *field_names: str,
    owner: str,
    description: str,
) -> AuditRequirement:
    return AuditRequirement(
        field_names=field_names,
        owner=owner,
        description=description,
    )


def _is_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True
