from __future__ import annotations

from lexrag.indexing.schemas import Chunk, ChunkMetadata
from lexrag.ingestion.deduplicator import VectorDeduplicator


def _chunk(
    *, chunk_id: str, doc_id: str, version: str, embedding: list[float]
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        document_version=version,
        source_path=f"/tmp/{doc_id}.pdf",
        doc_type="contract",
        page_num=1,
        section_title="Section",
        chunk_index=0,
        total_chunks=1,
    )
    return Chunk(
        chunk_id=chunk_id,
        text=f"text for {chunk_id}",
        metadata=metadata,
        embedding=embedding,
    )


def test_vector_deduplicator_suppresses_same_document_near_duplicate() -> None:
    deduplicator = VectorDeduplicator()
    first = _chunk(
        chunk_id="doc_a_0",
        doc_id="doc_a",
        version="v1",
        embedding=[1.0, 0.0, 0.0],
    )
    duplicate = _chunk(
        chunk_id="doc_a_1",
        doc_id="doc_a",
        version="v1",
        embedding=[0.9999, 0.0001, 0.0],
    )

    kept = deduplicator.deduplicate([first, duplicate])

    assert [chunk.chunk_id for chunk in kept] == ["doc_a_0"]
    assert deduplicator.last_report.decisions[1].decision == "suppressed"


def test_vector_deduplicator_keeps_cross_document_matches_for_provenance() -> None:
    deduplicator = VectorDeduplicator()
    existing = _chunk(
        chunk_id="doc_a_0",
        doc_id="doc_a",
        version="v1",
        embedding=[1.0, 0.0, 0.0],
    )
    candidate = _chunk(
        chunk_id="doc_b_0",
        doc_id="doc_b",
        version="v2",
        embedding=[0.9999, 0.0001, 0.0],
    )

    kept = deduplicator.deduplicate([candidate], existing_chunks=[existing])

    assert [chunk.chunk_id for chunk in kept] == ["doc_b_0"]
    assert deduplicator.last_report.decisions[0].decision == "cross_document_match"
