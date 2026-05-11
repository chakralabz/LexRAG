"""Lazy backend registry for parser orchestration.

The registry centralizes backend construction so routing code never needs to
know which backends are stateful, which ones need shared config, or which ones
were overridden by tests.
"""

from __future__ import annotations

from collections.abc import Callable
from inspect import signature
from typing import Any

from lexrag.ingestion.parser.backends import (
    BaseDocumentParser,
    DoclingParser,
    ManualRecoveryParser,
    OCROnlyParser,
    PyMuPDFParser,
    UnstructuredParser,
)
from lexrag.ingestion.parser.schemas.parser_backend import ParserBackend
from lexrag.ingestion.parser.schemas.parser_config import ParserConfig


class ParserBackendRegistry:
    """Provide parser backends by stable routing name.

    Backends are created lazily because some of them carry heavy startup costs
    such as model loading or runtime validation. The registry also gives tests a
    single override point for fake parsers.
    """

    def __init__(
        self,
        *,
        config: ParserConfig | None = None,
        primary_parser: BaseDocumentParser | Any | None = None,
        fallback_parser: BaseDocumentParser | Any | None = None,
        unstructured_parser: BaseDocumentParser | Any | None = None,
        ocr_parser: BaseDocumentParser | Any | None = None,
        manual_recovery_parser: BaseDocumentParser | Any | None = None,
    ) -> None:
        self.config = config or ParserConfig()
        # Provided parsers win over factories so tests and applications can
        # inject custom implementations without patching internal code paths.
        self._provided_parsers = {
            ParserBackend.DOCLING.value: primary_parser,
            ParserBackend.PYMUPDF.value: fallback_parser,
            ParserBackend.UNSTRUCTURED.value: unstructured_parser,
            ParserBackend.OCR_ONLY.value: ocr_parser,
            ParserBackend.MANUAL_RECOVERY.value: manual_recovery_parser,
        }
        self._parser_factories = self._build_factories()
        self._parsers: dict[str, BaseDocumentParser | Any] = {}

    def get(self, parser_name: str) -> BaseDocumentParser | Any:
        """Return the parser backend registered under ``parser_name``."""
        parser = self._parsers.get(parser_name)
        if parser is not None:
            return parser
        # Cache the first constructed backend instance so expensive objects such
        # as Docling converters are reused across documents.
        parser = self._build_parser(parser_name=parser_name)
        self._parsers[parser_name] = parser
        return parser

    def _build_factories(self) -> dict[str, Callable[[], BaseDocumentParser | Any]]:
        """Map stable backend ids to zero-argument construction callables."""
        return {
            ParserBackend.DOCLING.value: lambda: self._build_with_optional_config(
                factory=DoclingParser
            ),
            ParserBackend.PYMUPDF.value: PyMuPDFParser,
            ParserBackend.UNSTRUCTURED.value: UnstructuredParser,
            ParserBackend.OCR_ONLY.value: lambda: self._build_with_optional_config(
                factory=OCROnlyParser
            ),
            ParserBackend.MANUAL_RECOVERY.value: ManualRecoveryParser,
        }

    def _build_parser(self, *, parser_name: str) -> BaseDocumentParser | Any:
        """Resolve an override first, then fall back to the default factory."""
        provided = self._provided_parsers.get(parser_name)
        if provided is not None:
            return provided
        factory = self._parser_factories[parser_name]
        return factory()

    def _build_with_optional_config(
        self,
        *,
        factory: Callable[..., BaseDocumentParser | Any],
    ) -> BaseDocumentParser | Any:
        """Pass shared config only to factories that declare a config argument."""
        if "config" in signature(factory).parameters:
            return factory(config=self.config)
        return factory()
