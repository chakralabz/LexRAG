"""Top-level parser orchestration for one validated document.

This module is intentionally small because it is the package entrypoint most
callers depend on. It wires together three distinct responsibilities:

1. trust the upstream file-ingestion boundary for safety and MIME checks
2. choose the parser route from deterministic metadata and lightweight heuristics
3. convert parser backend output into a structured, provenance-rich result
"""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion import (
    FileIngestionConfig,
    FileIngestionReport,
    FileLoadResult,
    FileLoadService,
)
from lexrag.ingestion.parser.orchestration.manual_recovery_required_error import (
    ManualRecoveryRequiredError,
)
from lexrag.ingestion.parser.orchestration.parser_provenance_annotator import (
    ParserProvenanceAnnotator,
)
from lexrag.ingestion.parser.orchestration.parser_selection_strategy import (
    ParserSelectionStrategy,
)
from lexrag.ingestion.parser.schemas.document_parse_result import DocumentParseResult
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.ingestion.parser.schemas.parser_backend import ParserBackend
from lexrag.ingestion.parser.schemas.parser_config import ParserConfig
from lexrag.observability.logging_runtime import get_logger

from .parser_backend_registry import ParserBackendRegistry
from .parser_chain_executor import ParserChainExecutor

logger = get_logger(__name__)


class DocumentParser:
    """Production parser orchestrator for one file at a time.

    The class does not perform parsing logic itself. Instead, it coordinates
    routing, backend execution, and final provenance enrichment so each concern
    remains testable in isolation.
    """

    def __init__(
        self,
        *,
        config: ParserConfig | None = None,
        primary_parser: object | None = None,
        fallback_parser: object | None = None,
        unstructured_parser: object | None = None,
        ocr_parser: object | None = None,
        manual_recovery_parser: object | None = None,
        file_loader: FileLoadService | None = None,
        file_ingestion_config: FileIngestionConfig | None = None,
    ) -> None:
        # ParserConfig is shared across routing and stateful backends so a
        # single caller-supplied config affects selection, Docling, and OCR.
        self.config = config or ParserConfig()
        # The file loader is the trusted boundary for path resolution and file
        # validation. Parser code assumes anything beyond this point is already
        # allowed to be parsed.
        self.file_loader = file_loader or FileLoadService(config=file_ingestion_config)
        self.selector = ParserSelectionStrategy(config=self.config)
        self.registry = ParserBackendRegistry(
            config=self.config,
            primary_parser=primary_parser,
            fallback_parser=fallback_parser,
            unstructured_parser=unstructured_parser,
            ocr_parser=ocr_parser,
            manual_recovery_parser=manual_recovery_parser,
        )
        self.executor = ParserChainExecutor(registry=self.registry)
        self.annotator = ParserProvenanceAnnotator()
        self.last_result: DocumentParseResult | None = None

    def parse_document(self, path: str | Path) -> list[ParsedBlock]:
        """Parse a document and return canonical parsed blocks."""
        result = self.parse_with_report(path)
        return result.blocks

    def preload(self) -> None:
        """Warm heavy parser backends before serving live parse traffic.

        Startup warmup is optional but recommended in services, because it
        shifts model initialization and runtime validation away from the first
        user request.
        """
        for backend in self._preload_backends():
            parser = self.registry.get(backend.value)
            preload = getattr(parser, "preload", None)
            if callable(preload):
                preload()

    def _preload_backends(self) -> tuple[ParserBackend, ...]:
        """Return the backends whose cold start cost is user-visible."""
        return (
            ParserBackend.DOCLING,
            ParserBackend.OCR_ONLY,
        )

    def parse_with_report(self, path: str | Path) -> DocumentParseResult:
        """Parse a document and return the full structured parse report."""
        load_result = self.file_loader.load_file(path)
        return self.parse_loaded_file(load_result)

    def parse_loaded_file(self, load_result: FileLoadResult) -> DocumentParseResult:
        """Parse a file that has already passed through the loader boundary."""
        report = self._require_ingestion_report(load_result=load_result)
        validation = report.validation
        if not load_result.is_ready or not validation.is_valid:
            raise ValueError(validation.failure_reason or "validation_failed")
        resolved_path = Path(load_result.resolved_path or "")
        # Selection depends only on validated metadata and lightweight file
        # inspection. Individual parsers should not second-guess this routing.
        selection = self.selector.select(
            path=resolved_path,
            validation=validation,
            detection=report.detection,
        )
        result = self.executor.execute(path=resolved_path, selection=selection)
        if result.manual_recovery_required:
            self.last_result = result
            raise ManualRecoveryRequiredError(
                f"Manual recovery required for document: {resolved_path}",
                result=result,
            )
        # Provenance is attached only after a backend succeeds so every block in
        # the final result carries the same route- and attempt-level metadata.
        annotated_blocks = self.annotator.annotate(result)
        final_result = result.model_copy(update={"blocks": annotated_blocks})
        self.last_result = final_result
        self._log_success(path=resolved_path, result=final_result)
        return final_result

    def _log_success(self, *, path: Path, result: DocumentParseResult) -> None:
        """Emit one concise summary line for observability dashboards."""
        confidence = result.blocks[0].parse_confidence if result.blocks else 0.0
        logger.info(
            "Parsed document path=%s parser=%s fallback=%s attempts=%d blocks=%d confidence=%.2f",
            path,
            result.parser_used,
            result.fallback_used,
            len(result.attempts),
            len(result.blocks),
            confidence or 0.0,
        )

    def _require_ingestion_report(
        self,
        *,
        load_result: FileLoadResult,
    ) -> FileIngestionReport:
        """Require file-ingestion metadata before parser execution starts."""
        report = load_result.ingestion_report
        if report is not None:
            return report
        reason = load_result.rejection_reason or "load_failed"
        raise ValueError(reason)
