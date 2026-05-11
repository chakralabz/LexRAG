"""End-to-end ingestion pipeline orchestration."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, cast

from lexrag.indexing.bm25_store import BM25Store
from lexrag.indexing.coordinated_index_writer import CoordinatedIndexWriter
from lexrag.vector.qdrant_store import QdrantStore
from lexrag.indexing.schemas import Chunk
from lexrag.ingestion.chunker import Chunker
from lexrag.ingestion.ingestion_document_result import IngestionDocumentResult
from lexrag.ingestion.ingestion_summary import IngestionSummary
from lexrag.ingestion.normalizer import BlockNormalizer
from lexrag.ingestion.page_enricher import PagePayloadEnricher
from lexrag.ingestion.parser import DocumentParserProtocol, ParsedBlock
from lexrag.observability.logging_runtime import get_logger

logger = get_logger(__name__)


class IngestPipeline:
    """Coordinates the architecture-defined ingestion flow."""

    def __init__(
        self,
        *,
        parser: DocumentParserProtocol,
        chunker: Chunker,
        embedder: Any,
        qdrant_store: QdrantStore,
        bm25_store: BM25Store,
        index_writer: CoordinatedIndexWriter | None = None,
        normalizer: BlockNormalizer | None = None,
        page_enricher: PagePayloadEnricher | None = None,
    ) -> None:
        self.parser = self._validate_parser(parser=parser)
        self.chunker = chunker
        self.embedder = embedder
        self.qdrant_store = qdrant_store
        self.bm25_store = bm25_store
        self.index_writer = index_writer or CoordinatedIndexWriter(
            qdrant_store=qdrant_store,
            bm25_store=bm25_store,
        )
        self.normalizer = normalizer or BlockNormalizer()
        self.page_enricher = page_enricher or PagePayloadEnricher()

    def ingest_documents(self, paths: list[Path]) -> IngestionSummary:
        """Parse, normalize, chunk, embed, and index the provided documents."""
        chunks: list[Chunk] = []
        fallback_reasons: Counter[str] = Counter()
        parse_failures: Counter[str] = Counter()
        document_results: list[IngestionDocumentResult] = []
        fallback_documents = 0
        quarantined_documents = 0
        for path in paths:
            result, document_chunks = self._ingest_document(path=path)
            document_results.append(result)
            reason = result.fallback_reason
            failure = result.parse_failure_reason
            if reason is not None:
                fallback_documents += 1
                fallback_reasons[reason] += 1
            if failure is not None:
                parse_failures[failure] += 1
            if result.status == "quarantined":
                quarantined_documents += 1
            chunks.extend(document_chunks)
        embedded = self.embedder.embed_chunks(chunks)
        indexed = self._index_chunks(chunks=embedded)
        return IngestionSummary(
            documents_seen=len(paths),
            chunks_created=len(chunks),
            chunks_after_dedup=len(chunks),
            chunks_indexed=indexed,
            fallback_documents=fallback_documents,
            quarantined_documents=quarantined_documents,
            fallback_reason_counts=dict(fallback_reasons),
            parse_failure_counts=dict(parse_failures),
            document_results=document_results,
        )

    def _ingest_document(
        self,
        *,
        path: Path,
    ) -> tuple[IngestionDocumentResult, list[Chunk]]:
        """Ingest one document and return chunks plus provenance counters."""
        try:
            blocks, fallback_reason = self._parse_blocks(path=path)
        except Exception as exc:
            failure = self._classify_parse_failure(exc=exc)
            logger.warning(
                "Skipping ingest parse failure path=%s reason=%s", path, failure
            )
            return (
                IngestionDocumentResult(
                    path=str(path),
                    status=self._document_status(parse_failure_reason=failure),
                    chunks_created=0,
                    parse_failure_reason=failure,
                ),
                [],
            )
        enriched = cast(list[ParsedBlock], self.page_enricher.enrich(blocks, path=path))
        normalized = self.normalizer.normalize(enriched)
        chunks = self.chunker.chunk(normalized)
        logger.info(
            "Ingested path=%s blocks=%d normalized=%d chunks=%d fallback=%s",
            path,
            len(blocks),
            len(normalized),
            len(chunks),
            fallback_reason is not None,
        )
        return (
            IngestionDocumentResult(
                path=str(path),
                status="completed",
                chunks_created=len(chunks),
                fallback_reason=fallback_reason,
            ),
            chunks,
        )

    def _parse_blocks(self, *, path: Path) -> tuple[list[ParsedBlock], str | None]:
        """Parse one document while preserving fallback provenance."""
        result = self.parser.parse_with_report(path)
        return result.blocks, self._fallback_reason(blocks=result.blocks)

    def _fallback_reason(self, *, blocks: list[ParsedBlock]) -> str | None:
        """Resolve the primary fallback reason recorded on parsed blocks."""
        if not blocks:
            return None
        reason = blocks[0].metadata.get("fallback_reason_code")
        if isinstance(reason, str) and reason:
            return reason
        return None

    def _index_chunks(self, *, chunks: list[Chunk]) -> int:
        """Index chunks into dense and sparse stores in a consistent order."""
        return self.index_writer.index_chunks(chunks)

    def _classify_parse_failure(self, *, exc: Exception) -> str:
        """Map ingest parse failures onto stable observability labels."""
        message = str(exc).lower()
        if isinstance(exc, FileNotFoundError):
            return "file_not_found"
        if "unsupported_extension" in message:
            return "unsupported_extension"
        if "manual recovery required" in message:
            return "manual_recovery_required"
        if "empty" in message:
            return "empty_content"
        return exc.__class__.__name__

    def _document_status(self, *, parse_failure_reason: str) -> str:
        if parse_failure_reason == "manual_recovery_required":
            return "quarantined"
        return "failed"

    def _validate_parser(
        self,
        *,
        parser: DocumentParserProtocol,
    ) -> DocumentParserProtocol:
        """Reject parser implementations that bypass provenance reporting."""
        if isinstance(parser, DocumentParserProtocol):
            return parser
        raise TypeError(
            "IngestPipeline requires a parser implementing "
            "DocumentParserProtocol with parse_with_report() support"
        )
