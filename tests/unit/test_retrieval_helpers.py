from __future__ import annotations

from lexrag.indexing.schemas import Chunk, ChunkMetadata

from lexrag.retrieval import QueryDecomposer, TokenOverlapReranker


def _chunk(*, chunk_id: str, text: str, chunk_index: int) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata=ChunkMetadata(
            doc_id="doc_a",
            source_path="/tmp/doc_a.txt",
            doc_type="research_paper",
            page_num=1,
            section_title="Section",
            chunk_index=chunk_index,
            total_chunks=3,
        ),
    )


def test_query_decomposer_multihop_split() -> None:
    decomposer = QueryDecomposer()
    question = "Compare liability damages and negligence standards in tort law"
    assert decomposer.is_multihop(question) is True
    sub_queries = decomposer.decompose(question)
    assert 1 < len(sub_queries) <= 3


def test_token_overlap_reranker_prioritizes_matching_chunk() -> None:
    reranker = TokenOverlapReranker()
    chunks = [
        _chunk(chunk_id="doca_0", text="neural network optimization", chunk_index=0),
        _chunk(chunk_id="doca_1", text="liability damages negligence", chunk_index=1),
        _chunk(chunk_id="doca_2", text="contract law and remedies", chunk_index=2),
    ]
    ranked = reranker.rerank("liability damages in negligence", chunks, top_k=2)
    assert len(ranked) == 2
    assert ranked[0].chunk_id == "doca_1"
