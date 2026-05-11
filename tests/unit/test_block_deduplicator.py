from __future__ import annotations

from lexrag.ingestion.deduplicator import (
    BlockDeduplicationConfig,
    BlockDeduplicator,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


def test_block_deduplicator_drops_exact_duplicates() -> None:
    deduplicator = BlockDeduplicator()
    first = ParsedBlock(
        block_id="blk_1",
        page=1,
        section="Intro",
        text="This clause is identical.",
    )
    duplicate = ParsedBlock(
        block_id="blk_2",
        page=2,
        section="Intro",
        text="This clause is identical.",
    )

    kept = deduplicator.deduplicate([first, duplicate])

    assert [block.block_id for block in kept] == ["blk_1"]
    assert deduplicator.last_stats.total_skipped == 1
    assert kept[0].metadata["dedup_status"] == "kept"


def test_block_deduplicator_preserves_legal_sensitive_near_duplicates() -> None:
    deduplicator = BlockDeduplicator(
        config=BlockDeduplicationConfig(near_duplicate_threshold=0.70)
    )
    first = ParsedBlock(
        block_id="blk_1",
        page=1,
        section="Liability",
        block_type="clause",
        doc_type="contract",
        text="The supplier shall maintain cybersecurity insurance coverage.",
    )
    second = ParsedBlock(
        block_id="blk_2",
        page=2,
        section="Liability",
        block_type="clause",
        doc_type="contract",
        text="The supplier shall maintain cyber insurance coverage.",
    )

    kept = deduplicator.deduplicate([first, second])

    assert [block.block_id for block in kept] == ["blk_1", "blk_2"]
    assert kept[1].metadata["dedup_bypass_reason"] == "legal_sensitive"


def test_block_deduplicator_suppresses_repeated_header_footer_patterns() -> None:
    deduplicator = BlockDeduplicator()
    blocks = [
        ParsedBlock(
            block_id=f"hdr_{page}",
            page=page,
            section="Header",
            text="Confidential Draft",
            order_in_page=0,
        )
        for page in range(1, 6)
    ]
    body = ParsedBlock(
        block_id="body_1",
        page=1,
        section="Body",
        text="Unique legal analysis on the merits of the dispute.",
        order_in_page=2,
    )

    kept = deduplicator.deduplicate([*blocks, body])

    assert [block.block_id for block in kept] == ["body_1"]
