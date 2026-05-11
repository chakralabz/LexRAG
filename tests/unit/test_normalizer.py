from __future__ import annotations

from lexrag.ingestion.normalizer import (
    BlockNormalizationConfig,
    BlockNormalizer,
    OCRNormalizer,
    OCRPolicyNormalizer,
    ParserArtifactCleaner,
    SectionPathNormalizer,
    TableNormalizer,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


def test_block_normalizer_builds_section_path_and_metadata() -> None:
    normalizer = BlockNormalizer()
    blocks = [
        ParsedBlock(
            block_id="blk_h1",
            page=1,
            section="Definitions",
            block_type="heading",
            heading_level=1,
            text="Definitions",
        ),
        ParsedBlock(
            block_id="blk_p1",
            page=1,
            section="",
            text="Terms used in this agreement are defined below.",
        ),
    ]
    normalized = normalizer.normalize(blocks)
    assert len(normalized) == 2
    assert normalized[1].section == "Definitions"
    assert normalized[1].metadata["section_path"] == ["Definitions"]
    assert normalized[1].metadata["heading_anchor"] == "definitions"
    assert normalized[1].metadata["block_index"] == 1


def test_block_normalizer_preserves_code_block_format_and_marks_protected() -> None:
    normalizer = BlockNormalizer()
    blocks = [
        ParsedBlock(
            block_id="blk_code",
            page=1,
            section="Appendix",
            block_type="code",
            text="def f():\r\n    return 1  \r\n",
            markdown="```python\r\ndef f():\r\n    return 1  \r\n```",
        )
    ]
    normalized = normalizer.normalize(blocks)
    assert normalized[0].block_type == "code_block"
    assert normalized[0].text == "def f():\n    return 1"
    assert normalized[0].metadata["protected"] is True
    assert normalized[0].metadata["code_language"] == "python"


def test_section_path_normalizer_sets_safe_default_section() -> None:
    normalizer = SectionPathNormalizer(BlockNormalizationConfig())
    block = ParsedBlock(block_id="blk_1", page=1, section="", text="Body text.")
    normalized = normalizer.normalize(block)
    assert normalized.section == "Untitled Section"
    assert normalized.metadata["section_path"] == ["Untitled Section"]


def test_parser_artifact_cleaner_keeps_legal_confidential_banner() -> None:
    cleaner = ParserArtifactCleaner(BlockNormalizationConfig())
    block = ParsedBlock(
        block_id="blk_legal",
        page=1,
        section="Schedule A",
        doc_type="contract",
        text="CONFIDENTIAL\nClause text remains.\nPage 1 of 8",
    )
    normalized = cleaner.normalize(block)
    assert normalized.text == "CONFIDENTIAL\nClause text remains."


def test_ocr_normalizer_keeps_word_boundaries_for_high_confidence_text() -> None:
    normalizer = OCRNormalizer(BlockNormalizationConfig())
    block = ParsedBlock(
        block_id="blk_ocr",
        page=1,
        section="Scan",
        text="New\nYork regulation",
        is_ocr=True,
        confidence=0.95,
    )
    normalized = normalizer.normalize(block)
    assert normalized.text == "New York regulation"
    assert normalized.metadata["ocr_policy_action"] == "pass"


def test_ocr_policy_normalizer_marks_abstain_for_mid_confidence() -> None:
    normalizer = OCRPolicyNormalizer(reject_threshold=0.2, abstain_threshold=0.5)
    block = ParsedBlock(
        block_id="blk_ocr_mid",
        page=1,
        section="Scan",
        text="Entity disclosure text",
        is_ocr=True,
        confidence=0.35,
    )
    normalized = normalizer.normalize(block)
    assert normalizer.should_drop(normalized) is False
    assert normalized.metadata["ocr_policy_action"] == "abstain"


def test_block_normalizer_drops_rejected_low_confidence_ocr_blocks() -> None:
    normalizer = BlockNormalizer()
    blocks = [
        ParsedBlock(
            block_id="blk_ocr_low",
            page=1,
            section="Scan",
            text="N o i s y",
            is_ocr=True,
            confidence=0.1,
        ),
        ParsedBlock(
            block_id="blk_2",
            page=1,
            section="Doc",
            text="Valid sentence.",
        ),
    ]
    normalized = normalizer.normalize(blocks)
    assert [block.block_id for block in normalized] == ["blk_2"]


def test_table_normalizer_pads_ragged_rows_and_marks_table_protected() -> None:
    normalizer = TableNormalizer(BlockNormalizationConfig())
    block = ParsedBlock(
        block_id="blk_table",
        page=2,
        section="Metrics",
        block_type="table",
        text="Metric | Value\nMRR@5\nRecall@10 | 0.90",
    )
    normalized = normalizer.normalize(block)
    assert normalized.markdown == (
        "| Metric | Value |\n| --- | --- |\n| MRR@5 |  |\n| Recall@10 | 0.90 |"
    )
    assert normalized.metadata["table_merged_cells_suspected"] is True
