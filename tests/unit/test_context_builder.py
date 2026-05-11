from __future__ import annotations

from lexrag.citation import CitationDocument
from lexrag.context_builder import LLMContextBuilder
from lexrag.indexing.schemas import Chunk, ChunkMetadata


def _chunk(
    *,
    chunk_id: str,
    text: str,
    page: int,
    score: float,
    quality: float,
    source_block_ids: list[str],
) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_1",
        source_path="/tmp/msa-v3.pdf",
        chunk_index=page - 1,
        total_chunks=10,
        page_start=page,
        page_end=page,
        section_title="Definitions",
        section_path=["Part I", "Definitions"],
        source_block_ids=source_block_ids,
        chunk_quality_score=quality,
        metadata={"reranker": {"score": score, "rank": page}},
    )
    return Chunk(chunk_id=chunk_id, text=text, metadata=metadata)


def test_context_builder_deduplicates_and_formats_sources() -> None:
    builder = LLMContextBuilder()
    chunks = [
        _chunk(
            chunk_id="doc_1_chunk_1",
            text="The liability cap is $100,000 under the agreement.",
            page=1,
            score=0.9,
            quality=0.9,
            source_block_ids=["a"],
        ),
        _chunk(
            chunk_id="doc_1_chunk_2",
            text="The liability cap is $100,000 under the agreement.",
            page=2,
            score=0.8,
            quality=0.7,
            source_block_ids=["b"],
        ),
    ]
    window = builder.build(
        query="What is the liability cap?",
        chunks=chunks,
        document_catalog={
            "doc_1": CitationDocument(document_id="doc_1", title="MSA v3")
        },
    )

    assert window.num_sources == 1
    assert (
        "[SOURCE 1 | doc: MSA v3 | page 1 | section: Part I > Definitions]"
        in window.formatted_context
    )


def test_context_builder_preserves_sole_query_term_during_compression() -> None:
    builder = LLMContextBuilder()
    builder.config = builder.config.model_copy(update={"max_context_tokens": 8})
    builder.compressor.config = builder.config
    chunks = [
        _chunk(
            chunk_id="doc_1_chunk_1",
            text="Remedies include injunctive relief for misuse of trade secrets.",
            page=1,
            score=0.95,
            quality=0.2,
            source_block_ids=["a"],
        ),
        _chunk(
            chunk_id="doc_1_chunk_2",
            text="Payment terms are net thirty days after invoice.",
            page=2,
            score=0.96,
            quality=0.1,
            source_block_ids=["b"],
        ),
    ]

    window = builder.build(
        query="What remedies exist for trade secrets?", chunks=chunks
    )

    assert any("trade secrets" in source.chunk.text for source in window.sources)


def test_context_builder_emits_conflict_warning() -> None:
    builder = LLMContextBuilder()
    chunks = [
        _chunk(
            chunk_id="doc_1_chunk_1",
            text="The cap is $100,000 for direct damages.",
            page=1,
            score=0.9,
            quality=0.8,
            source_block_ids=["a"],
        ),
        _chunk(
            chunk_id="doc_1_chunk_2",
            text="The cap is $250,000 for direct damages.",
            page=2,
            score=0.8,
            quality=0.8,
            source_block_ids=["b"],
        ),
    ]

    window = builder.build(query="What is the damages cap?", chunks=chunks)

    assert window.conflict_detected is True
    assert "Potential conflict across amounts" in window.warnings[0]
