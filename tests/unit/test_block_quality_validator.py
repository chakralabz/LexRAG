from __future__ import annotations

from lexrag.ingestion.block_quality import BlockQualityValidator
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


def test_block_quality_validator_drops_empty_and_micro_blocks() -> None:
    validator = BlockQualityValidator()
    empty = ParsedBlock(block_id="blk_1", page=1, section="Doc", text="   ")
    micro = ParsedBlock(block_id="blk_2", page=1, section="Doc", text="too short")
    body = ParsedBlock(
        block_id="blk_3",
        page=1,
        section="Doc",
        text="This is a substantive paragraph with enough signal to keep.",
    )

    kept = validator.validate([empty, micro, body])

    assert [block.block_id for block in kept] == ["blk_3"]


def test_block_quality_validator_drops_duplicate_of_known_dropped_block() -> None:
    validator = BlockQualityValidator()
    junk = ParsedBlock(
        block_id="blk_1",
        page=1,
        section="Doc",
        text="@@@@ #### !!!! $$$$ %%%% ^^^^",
    )
    repeated = ParsedBlock(
        block_id="blk_2",
        page=2,
        section="Doc",
        text="@@@@ #### !!!! $$$$ %%%% ^^^^",
    )

    kept = validator.validate([junk, repeated])

    assert kept == []
    assert validator.last_assessments[1].drop_reason == "duplicate_dropped_block"


def test_block_quality_validator_flags_tables_and_truncated_blocks() -> None:
    validator = BlockQualityValidator()
    table = ParsedBlock(
        block_id="tbl_1",
        page=1,
        section="Financials",
        block_type="table",
        text="Year|Revenue\n2024|100|200",
    )
    truncated = ParsedBlock(
        block_id="blk_2",
        page=1,
        section="Financials",
        text="The agreement remains enforceable if the parties continue",
    )
    next_page = ParsedBlock(
        block_id="blk_3",
        page=2,
        section="Financials",
        text="to perform under the same commercial terms.",
    )

    kept = validator.validate([table, truncated, next_page])

    assert kept[0].metadata["quality_status"] == "flagged"
    assert "malformed_table" in kept[0].metadata["quality_flags"]
    assert "truncated_block" in kept[1].metadata["quality_flags"]
