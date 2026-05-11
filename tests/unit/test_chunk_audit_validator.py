from __future__ import annotations

from datetime import UTC, datetime

from lexrag.audit import ChunkAuditValidator
from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata


def _chunk(*, ingestion_timestamp: datetime | None) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc-1",
        document_version="v1",
        source_path="/tmp/doc-1.pdf",
        doc_type="policy",
        chunk_index=0,
        total_chunks=2,
        source_blocks=["b1", "b2"],
        page_start=1,
        page_end=2,
        heading_anchor="risk-factors",
        chunking_strategy="semantic",
        overlap_prev=False,
        overlap_next=True,
        next_chunk_id="doc-1_1",
        parser_used=["docling"],
        fallback_used=False,
        ocr_used=False,
        parse_confidence=0.93,
        chunk_quality_score=0.88,
        ingestion_timestamp=ingestion_timestamp,
        embedding_model="BAAI/bge-m3",
        embedding_model_version="1.0.0",
    )
    return Chunk(chunk_id="doc-1_0", text="chunk text", metadata=metadata)


def test_chunk_audit_validator_accepts_complete_chunk() -> None:
    validator = ChunkAuditValidator()

    result = validator.validate_chunk(
        _chunk(ingestion_timestamp=datetime(2026, 1, 1, tzinfo=UTC))
    )

    assert result.passed is True
    assert result.completeness_score == 1.0
    assert result.issues == []


def test_chunk_audit_validator_flags_missing_required_fields() -> None:
    validator = ChunkAuditValidator()

    result = validator.validate_chunk(_chunk(ingestion_timestamp=None))

    assert result.passed is False
    assert result.completeness_score < 1.0
    assert [issue.field_name for issue in result.issues] == ["ingestion_timestamp"]
