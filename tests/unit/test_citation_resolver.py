from __future__ import annotations

from lexrag.citation import CitationDocument, CitationResolver
from lexrag.indexing.schemas import Chunk, ChunkMetadata


def _make_chunk(
    *,
    chunk_id: str,
    chunk_index: int,
    doc_id: str = "doc_123",
    source_path: str = "/tmp/master-services-agreement-v3.pdf",
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id=doc_id,
        document_version="v3",
        source_path=source_path,
        chunk_index=chunk_index,
        total_chunks=2,
        page_start=4 + chunk_index,
        page_end=4 + chunk_index,
        section_title="Definitions",
        section_path=["Part I", "Section 1.2", "Definitions"],
        heading_anchor="section-1-2-definitions",
        source_block_ids=[f"block_{chunk_index}"],
    )
    return Chunk(chunk_id=chunk_id, text="Grounding text", metadata=metadata)


def test_resolve_enriches_citations_with_catalog_metadata() -> None:
    resolver = CitationResolver()
    chunk = _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=0)
    document = CitationDocument(
        document_id="doc_123",
        title="Master Services Agreement v3",
        version="v3",
    )

    resolution = resolver.resolve([chunk], document_catalog={"doc_123": document})

    assert resolution.unresolved_document_ids == []
    citation = resolution.citations[0]
    assert citation.citation_id == 1
    assert citation.document_title == "Master Services Agreement v3"
    assert citation.document_version == "v3"
    assert citation.page == 4
    assert citation.section == "Part I > Section 1.2 > Definitions"
    assert citation.heading_anchor == "section-1-2-definitions"
    assert citation.chunk_id == "doc_123_chunk_1"
    assert citation.confidence > 0.8


def test_resolve_falls_back_to_source_path_title_when_catalog_missing() -> None:
    resolver = CitationResolver()
    chunk = _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=0)

    resolution = resolver.resolve([chunk])

    assert resolution.unresolved_document_ids == ["doc_123"]
    assert resolution.citations[0].document_title == "master-services-agreement-v3"


def test_validate_answer_detects_orphan_citation_ids() -> None:
    resolver = CitationResolver()
    chunks = [
        _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=0),
        _make_chunk(chunk_id="doc_123_chunk_2", chunk_index=1),
    ]
    resolution = resolver.resolve(chunks)

    validation = resolver.validate_answer(
        "The agreement defines services [1] and references an unknown clause [3].",
        resolution=resolution,
    )

    assert validation.is_valid is False
    assert validation.cited_citation_ids == [1]
    assert validation.orphan_citation_ids == [3]
    assert validation.uncited_citation_ids == [2]
    assert validation.issues[0].code == "orphan_citation_id"


def test_validate_answer_expands_grouped_citations() -> None:
    resolver = CitationResolver()
    chunks = [
        _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=0),
        _make_chunk(chunk_id="doc_123_chunk_2", chunk_index=1),
    ]
    resolution = resolver.resolve(chunks)

    validation = resolver.validate_answer(
        "Both obligations and remedies are covered [1, 2].",
        resolution=resolution,
    )

    assert validation.is_valid is True
    assert [reference.citation_id for reference in validation.references] == [1, 2]
    assert validation.cited_citation_ids == [1, 2]
    assert validation.orphan_citation_ids == []


def test_resolve_rejects_duplicate_chunk_ids() -> None:
    resolver = CitationResolver()
    duplicate_chunks = [
        _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=0),
        _make_chunk(chunk_id="doc_123_chunk_1", chunk_index=1),
    ]

    try:
        resolver.resolve(duplicate_chunks)
    except ValueError as error:
        assert str(error) == "citation resolution requires unique chunk_ids"
    else:
        raise AssertionError("Expected duplicate chunk IDs to be rejected")
