from datetime import date

import pytest
from pydantic import ValidationError

from indexing.schema import Chunk, ChunkMetadata, QAPair


def _metadata() -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc_abc123",
        source_path="data/raw/sample.pdf",
        doc_type="sec_filing",
        jurisdiction="US-DE",
        doc_date=date(2024, 1, 1),
        page_num=3,
        section_title="Risk Factors",
        chunk_index=2,
        total_chunks=12,
    )


def test_chunk_construction() -> None:
    chunk = Chunk(chunk_id="doc_abc123_2", text="Sample text", metadata=_metadata())

    assert chunk.metadata.doc_type == "sec_filing"
    assert chunk.text == "Sample text"


def test_chunk_id_format_validation() -> None:
    with pytest.raises(ValidationError):
        Chunk(chunk_id="invalid-format", text="Sample text", metadata=_metadata())


def test_qa_pair_difficulty_enum_validation() -> None:
    QAPair(
        question_id="q_001",
        question="What is X?",
        gold_answer="X is Y",
        gold_chunk_ids=["doc_abc123_2"],
        difficulty="factoid",
    )

    with pytest.raises(ValidationError):
        QAPair(
            question_id="q_002",
            question="What is Z?",
            gold_answer="Z is W",
            gold_chunk_ids=["doc_abc123_3"],
            difficulty="unknown",  # type: ignore[arg-type]
        )
