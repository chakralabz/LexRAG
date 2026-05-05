"""Execute the configured parser chain deterministically.

The executor is deliberately dumb about routing. Its job is only to iterate the
already-selected parser order, capture structured attempt metadata, and stop at
the first backend that returns usable blocks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.builders.parsed_block_factory import ParsedBlockFactory
from lexrag.ingestion.parser.orchestration.error_classification import (
    classify_parse_error,
)
from lexrag.ingestion.parser.schemas.document_parse_result import DocumentParseResult
from lexrag.ingestion.parser.schemas.parse_attempt import ParseAttempt
from lexrag.ingestion.parser.schemas.parser_backend import ParserBackend
from lexrag.ingestion.parser.schemas.parser_selection import ParserSelection

from .parser_backend_registry import ParserBackendRegistry


class ParserChainExecutor:
    """Run parser backends in the selected order until one succeeds."""

    def __init__(
        self,
        *,
        registry: ParserBackendRegistry,
        block_factory: ParsedBlockFactory | None = None,
    ) -> None:
        # ParsedBlockFactory handles a subtle compatibility problem: some
        # backends return full ParsedBlock objects while others return simpler
        # payloads. The executor always normalizes before returning success.
        self.registry = registry
        self.block_factory = block_factory or ParsedBlockFactory()

    def execute(
        self,
        *,
        path: Path,
        selection: ParserSelection,
    ) -> DocumentParseResult:
        """Execute the parser chain and return a structured parse result."""
        attempts: list[ParseAttempt] = []
        for order, parser_name in enumerate(selection.parser_order, start=1):
            # The registry hides whether the backend was injected, memoized, or
            # built lazily from shared config.
            parser = self.registry.get(parser_name)
            parsed, attempt = self._attempt_parse(
                path=path,
                parser_name=parser_name,
                parser=parser,
                fallback_step=order,
            )
            attempts.append(attempt)
            if parsed is None:
                continue
            # The first non-empty parse result wins. Fallback ordering is the
            # authoritative policy, so later parsers never "improve" success.
            return self._build_success_result(
                selection=selection,
                attempts=attempts,
                parser_name=parser_name,
                parsed=parsed,
            )
        return self._build_failure_result(selection=selection, attempts=attempts)

    def _attempt_parse(
        self,
        *,
        path: Path,
        parser_name: str,
        parser: Any,
        fallback_step: int,
    ) -> tuple[list | None, ParseAttempt]:
        """Run one backend and capture either success or a structured failure."""
        try:
            parsed = parser.parse(path)
        except Exception as exc:
            return None, self._failed_attempt(
                parser_name=parser_name,
                fallback_step=fallback_step,
                reason=classify_parse_error(exc),
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
        if not parsed:
            # Empty output is treated as failure because downstream stages cannot
            # distinguish "parser succeeded but found nothing" from parser loss.
            return None, self._empty_attempt(
                parser_name=parser_name,
                fallback_step=fallback_step,
            )
        blocks = self.block_factory.build_blocks(
            path=path,
            parser_name=parser_name,
            parsed_items=list(parsed),
        )
        return blocks, self._successful_attempt(
            parser_name=parser_name,
            fallback_step=fallback_step,
            produced_blocks=len(blocks),
        )

    def _failed_attempt(
        self,
        *,
        parser_name: str,
        fallback_step: int,
        reason: str,
        error_type: str,
        error_message: str,
    ) -> ParseAttempt:
        """Create a failed attempt record without losing the original error."""
        return ParseAttempt(
            parser_name=parser_name,
            succeeded=False,
            fallback_step=fallback_step,
            produced_blocks=0,
            failure_reason=reason,
            error_type=error_type,
            error_message=error_message,
        )

    def _empty_attempt(
        self,
        *,
        parser_name: str,
        fallback_step: int,
    ) -> ParseAttempt:
        # Empty parser output is normalized into the same failure shape as hard
        # exceptions so audits can reason over one attempt schema.
        return self._failed_attempt(
            parser_name=parser_name,
            fallback_step=fallback_step,
            reason="primary_empty_output",
            error_type="RuntimeError",
            error_message=f"{parser_name} returned no parsed blocks",
        )

    def _successful_attempt(
        self,
        *,
        parser_name: str,
        fallback_step: int,
        produced_blocks: int,
    ) -> ParseAttempt:
        """Create the success attempt record for the winning backend."""
        return ParseAttempt(
            parser_name=parser_name,
            succeeded=True,
            fallback_step=fallback_step,
            produced_blocks=produced_blocks,
        )

    def _build_success_result(
        self,
        *,
        selection: ParserSelection,
        attempts: list[ParseAttempt],
        parser_name: str,
        parsed: list,
    ) -> DocumentParseResult:
        """Build the terminal success result for the first winning backend."""
        fallback_used = None
        if parser_name != selection.primary_parser_name:
            fallback_used = parser_name
        # OCR-only parsing is represented explicitly because generation and eval
        # code often want to distinguish OCR-derived content from native text.
        ocr_used = parser_name if parser_name == ParserBackend.OCR_ONLY.value else None
        return DocumentParseResult(
            blocks=parsed,
            attempts=attempts,
            selection=selection,
            parser_used=parser_name,
            fallback_used=fallback_used,
            ocr_used=ocr_used,
            scanned_pdf=selection.scanned_pdf,
            encrypted=selection.encrypted,
            image_heavy=selection.image_heavy,
            partial_extraction=False,
            manual_recovery_required=False,
        )

    def _build_failure_result(
        self,
        *,
        selection: ParserSelection,
        attempts: list[ParseAttempt],
    ) -> DocumentParseResult:
        """Build the terminal failure result when every backend is exhausted."""
        return DocumentParseResult(
            blocks=[],
            attempts=attempts,
            selection=selection,
            parser_used=ParserBackend.MANUAL_RECOVERY.value,
            fallback_used=ParserBackend.MANUAL_RECOVERY.value,
            ocr_used=None,
            scanned_pdf=selection.scanned_pdf,
            encrypted=selection.encrypted,
            image_heavy=selection.image_heavy,
            partial_extraction=False,
            manual_recovery_required=True,
        )
