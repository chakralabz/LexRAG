from __future__ import annotations

from lexrag.ingestion.chunker.block_aware_semantic_planner import (
    BlockAwareSemanticPlanner,
)
from lexrag.ingestion.chunker.chunk_model_factory import ChunkModelFactory
from lexrag.ingestion.chunker.schemas.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.semantic_chunker import SemanticChunker
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


def test_semantic_planner_assigns_architecture_aligned_strategies() -> None:
    planner = BlockAwareSemanticPlanner(
        config=ChunkingConfig(
            min_chunk_tokens=1,
            max_chunk_tokens=4,
            overlap_tokens=1,
            target_chunk_tokens=4,
        )
    )
    heading = ParsedBlock(
        block_id="h1",
        page=1,
        section="Definitions",
        block_type="heading",
        text="Definitions",
    )
    table = ParsedBlock(
        block_id="t1",
        page=1,
        section="Definitions",
        block_type="table",
        text="Revenue 2025 100 200",
    )
    long_paragraph = ParsedBlock(
        block_id="p1",
        page=1,
        section="Definitions",
        text="one two three four five six seven eight",
    )

    plans = planner.plan([heading, table, long_paragraph])

    assert plans[0].chunking_strategy == "heading_anchored"
    assert plans[0].section_boundary is True
    assert plans[1].chunking_strategy == "table_aware"
    assert plans[1].standalone is True
    assert plans[2].chunking_strategy == "sliding_window"


def test_semantic_chunker_keeps_heading_context_with_following_content() -> None:
    chunker = SemanticChunker()
    heading = ParsedBlock(
        block_id="h1",
        page=1,
        section="Risk Factors",
        block_type="heading",
        text="Risk Factors",
    )
    paragraph = ParsedBlock(
        block_id="p1",
        page=1,
        section="Risk Factors",
        text="The company may face supply chain disruptions.",
    )

    chunks = chunker.chunk([heading, paragraph])

    assert len(chunks) == 1
    assert chunks[0].text.startswith("Risk Factors")
    assert chunks[0].metadata.heading_anchor == "Risk Factors"
    assert chunks[0].metadata.chunking_strategy == "semantic_merge"


def test_semantic_chunker_preserves_table_as_standalone_chunk() -> None:
    chunker = SemanticChunker()
    table = ParsedBlock(
        block_id="tbl_1",
        page=2,
        section="Financials",
        block_type="table",
        text="Revenue | 2025\n100 | 200",
    )

    chunks = chunker.chunk([table])

    assert len(chunks) == 1
    assert chunks[0].metadata.chunk_type == "table"
    assert chunks[0].metadata.contains_table is True
    assert chunks[0].metadata.chunking_strategy == "table_aware"


def test_semantic_chunker_filters_duplicate_and_low_quality_blocks() -> None:
    chunker = SemanticChunker()
    duplicate_a = ParsedBlock(
        block_id="dup_1",
        page=1,
        section="Intro",
        text="The company must maintain annual compliance certifications.",
    )
    duplicate_b = ParsedBlock(
        block_id="dup_2",
        page=2,
        section="Intro",
        text="The company must maintain annual compliance certifications.",
    )
    noisy = ParsedBlock(
        block_id="ocr_1",
        page=3,
        section="Intro",
        text="N e w  Y o r k",
        is_ocr=True,
        confidence=0.20,
    )
    body = ParsedBlock(
        block_id="body_1",
        page=4,
        section="Intro",
        text="Management reviewed the controls and found no material weakness.",
    )

    chunks = chunker.chunk([duplicate_a, duplicate_b, noisy, body])

    assert len(chunks) == 1
    assert "material weakness" in chunks[0].text


def test_chunk_model_factory_adds_source_spans_for_auditability() -> None:
    first = ParsedBlock(block_id="blk_1", page=1, section="Doc", text="First clause.")
    second = ParsedBlock(block_id="blk_2", page=1, section="Doc", text="Second clause.")
    payload = {
        "text": "First clause.\n\nSecond clause.",
        "source_blocks": [first, second],
        "chunking_strategy": "semantic_merge",
    }

    chunk = ChunkModelFactory().build_chunks([payload], parsed_blocks=[first, second])[
        0
    ]
    spans = chunk.metadata.metadata["source_spans"]

    assert len(spans) == 2
    assert spans[0]["block_id"] == "blk_1"
    assert spans[0]["match_type"] == "exact"
    assert spans[1]["block_id"] == "blk_2"
    assert spans[1]["start_char"] > spans[0]["end_char"]


def test_chunk_model_factory_uses_token_anchor_when_exact_text_differs() -> None:
    block = ParsedBlock(
        block_id="blk_table_1",
        page=1,
        section="Financials",
        block_type="table",
        text="Revenue 2025 100 200",
    )
    payload = {
        "text": "| Revenue | 2025 |\n| 100 | 200 |",
        "source_blocks": [block],
        "chunking_strategy": "table_aware",
    }

    chunk = ChunkModelFactory().build_chunks([payload], parsed_blocks=[block])[0]
    span = chunk.metadata.metadata["source_spans"][0]

    assert span["block_id"] == "blk_table_1"
    assert span["matched"] is True
    assert span["match_type"] == "token_anchor"
