"""Public audit validation service."""

from __future__ import annotations

from lexrag.audit.chunk_audit_validator import ChunkAuditValidator
from lexrag.audit.schemas import AuditValidationResult
from lexrag.indexing.schemas import Chunk


class AuditService:
    """Validate audit metadata completeness for canonical chunks."""

    def __init__(self, *, validator: ChunkAuditValidator | None = None) -> None:
        self._validator = validator or ChunkAuditValidator()

    def validate_chunks(self, chunks: list[Chunk]) -> list[AuditValidationResult]:
        """Validate one chunk collection against the audit contract."""
        return self._validator.validate_chunks(chunks)

    def auditability_score(self, chunks: list[Chunk]) -> float:
        """Return the aggregate auditability score for one chunk collection."""
        return self._validator.auditability_score(chunks)
