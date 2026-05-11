from __future__ import annotations

from lexrag.citation import CitationDocument
from lexrag.context_builder import LLMContextBuilder
from lexrag.generation import AnswerGenerator
from lexrag.generation.llm_backend import LLMBackend
from lexrag.generation.schemas import GenerationRequest
from lexrag.indexing.schemas import Chunk, ChunkMetadata


class FakeBackend(LLMBackend):
    def __init__(self, *, response: str) -> None:
        self.response = response

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        return self.response


def _chunk(*, chunk_id: str, text: str, page: int) -> Chunk:
    metadata = ChunkMetadata(
        doc_id="doc_1",
        source_path="/tmp/msa-v3.pdf",
        chunk_index=page - 1,
        total_chunks=3,
        page_start=page,
        page_end=page,
        section_title="Liability",
        section_path=["Part II", "Liability"],
        source_block_ids=[f"block_{page}"],
        metadata={"retrieval": {"score": 0.8, "rank": page}},
    )
    return Chunk(chunk_id=chunk_id, text=text, metadata=metadata)


def _request() -> GenerationRequest:
    builder = LLMContextBuilder()
    window = builder.build(
        query="What is the liability cap?",
        chunks=[
            _chunk(
                chunk_id="doc_1_chunk_1",
                text="The liability cap is $100,000.",
                page=1,
            )
        ],
        document_catalog={
            "doc_1": CitationDocument(document_id="doc_1", title="MSA v3")
        },
    )
    return GenerationRequest(
        question="What is the liability cap?", context_window=window
    )


def test_answer_generator_validates_supported_answer() -> None:
    generator = AnswerGenerator(
        backend=FakeBackend(response="The liability cap is $100,000 [1].")
    )

    response = generator.generate(_request())

    assert response.validation.is_valid is True
    assert response.validation.citation_validation.cited_citation_ids == [1]
    assert response.validation.is_abstained is False


def test_answer_generator_rejects_orphan_citation_ids() -> None:
    generator = AnswerGenerator(
        backend=FakeBackend(response="The liability cap is $100,000 [2].")
    )

    response = generator.generate(_request())

    assert response.validation.is_valid is False
    assert response.validation.citation_validation.orphan_citation_ids == [2]


def test_answer_generator_detects_abstention_and_pii() -> None:
    generator = AnswerGenerator(
        backend=FakeBackend(
            response="The answer is not in the provided sources. Contact legal@example.com."
        )
    )

    response = generator.generate(_request())

    assert response.validation.is_abstained is True
    assert response.validation.is_valid is False
    assert response.validation.pii_findings[0].kind == "email"
