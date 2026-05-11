from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from lexrag.indexing.bm25_store import BM25Store
from lexrag.ingestion.chunker.fixed_size_chunker import FixedSizeChunker
from lexrag.ingestion.embeddings.build_embedder import build_embedder
from lexrag.ingestion.parser.document_parser import FallbackDocumentParser
from lexrag.ingestion.parser.schemas.document_parse_result import DocumentParseResult
from lexrag.ingestion.parser.schemas.parse_attempt import ParseAttempt
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.ingestion.parser.schemas.parser_selection import ParserSelection
from lexrag.ingestion.pipeline import IngestPipeline
from lexrag.vector.qdrant_store import QdrantStore


class StubDocumentParser:
    def __init__(self, *, blocks: list[ParsedBlock]) -> None:
        self._blocks = blocks

    def parse_document(self, path: Path) -> list[ParsedBlock]:
        return self.parse_with_report(path).blocks

    def parse_with_report(self, path: Path) -> DocumentParseResult:
        return DocumentParseResult(
            blocks=self._blocks,
            attempts=[
                ParseAttempt(
                    parser_name="stub",
                    succeeded=True,
                    fallback_step=1,
                    produced_blocks=len(self._blocks),
                )
            ],
            selection=ParserSelection(
                primary_parser_name="stub",
                parser_order=["stub"],
                fallback_chain=[],
                route_reason=f"stub:{path.suffix.lower()}",
                requires_ocr=False,
                scanned_pdf=False,
                image_heavy=False,
                encrypted=False,
            ),
            parser_used="stub",
            fallback_used=None,
            ocr_used=None,
            scanned_pdf=False,
            encrypted=False,
            image_heavy=False,
            partial_extraction=False,
            manual_recovery_required=False,
        )


def _memory_pipeline(
    *, parser: StubDocumentParser | FallbackDocumentParser
) -> IngestPipeline:
    return IngestPipeline(
        parser=parser,
        chunker=FixedSizeChunker(chunk_size=64, overlap=8),
        embedder=build_embedder(mode="deterministic-test-only"),
        qdrant_store=QdrantStore(backend="memory"),
        bm25_store=BM25Store(backend="memory"),
    )


@pytest.mark.integration
def test_pipeline_uses_fallback_parser_and_indexes_chunks(tmp_path: Path) -> None:
    doc_path = tmp_path / "fallback_doc.pdf"
    doc_path.write_bytes(b"%PDF-1.4\nplaceholder")
    primary = Mock()
    primary.parse.side_effect = RuntimeError("primary parser failed")
    fallback = Mock()
    fallback.parse.return_value = [
        ParsedBlock(
            block_id="blk_fallback_1",
            page=1,
            section="Page 1",
            text="Fallback extraction text for legal clause.",
            parser_used="pymupdf",
        )
    ]
    parser = FallbackDocumentParser(primary_parser=primary, fallback_parser=fallback)
    pipeline = _memory_pipeline(parser=parser)
    summary = pipeline.ingest_documents([doc_path])
    assert summary.chunks_indexed > 0
    assert summary.fallback_reason_counts["primary_parse_error"] == 1
    indexed = pipeline.qdrant_store.search_dense([0.0] * 1024, limit=10)
    assert indexed
    assert indexed[0].metadata.metadata["is_fallback_used"] is True
    assert indexed[0].metadata.metadata["fallback_reason_code"] == "primary_parse_error"


@pytest.mark.integration
def test_pipeline_drops_low_confidence_ocr_and_keeps_table_metadata(
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "ocr_table.pdf"
    doc_path.write_text("placeholder", encoding="utf-8")
    parser = StubDocumentParser(
        blocks=[
            ParsedBlock(
                block_id="blk_ocr_reject",
                page=1,
                section="Scan",
                text="N e w  Y o r k",
                is_ocr=True,
                confidence=0.10,
            ),
            ParsedBlock(
                block_id="blk_table_keep",
                page=1,
                section="Financials",
                block_type="table",
                text="Revenue | 2025\n100 | 200",
            ),
        ]
    )
    pipeline = _memory_pipeline(parser=parser)
    summary = pipeline.ingest_documents([doc_path])
    assert summary.chunks_created >= 1
    results = pipeline.bm25_store.search_bm25("Revenue 2025", limit=5)
    assert results
    table_chunk = results[0]
    spans = table_chunk.metadata.metadata["source_spans"]
    assert table_chunk.metadata.contains_table is True
    assert spans[0]["block_id"] == "blk_table_keep"


def test_pipeline_rejects_duck_typed_parser_without_report_support() -> None:
    with pytest.raises(TypeError, match="DocumentParserProtocol"):
        _memory_pipeline(parser=Mock(parse_document=Mock()))
