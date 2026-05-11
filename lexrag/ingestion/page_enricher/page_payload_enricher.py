"""Page/block payload enrichment with canonical source metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from lexrag.ingestion.page_enricher.document_type_resolver import DocumentTypeResolver
from lexrag.ingestion.page_enricher.heuristic_document_type_resolver import (
    HeuristicDocumentTypeResolver,
)
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class PagePayloadEnricher:
    """Populate doc identity and source metadata for parser payloads."""

    def __init__(self, *, resolver: DocumentTypeResolver | None = None) -> None:
        self.resolver = resolver or HeuristicDocumentTypeResolver()

    def enrich(
        self,
        payloads: list[ParsedBlock] | list[dict[str, Any]],
        *,
        path: Path,
    ) -> list[ParsedBlock] | list[dict[str, Any]]:
        """Return payloads with doc-level fields set consistently."""
        if not payloads:
            return []
        doc_type = self.resolver.resolve(path=path)
        first_payload = payloads[0]
        if isinstance(first_payload, ParsedBlock):
            blocks = cast(list[ParsedBlock], payloads)
            return self._enrich_blocks(payloads=blocks, path=path, doc_type=doc_type)
        dict_payloads = cast(list[dict[str, Any]], payloads)
        return self._enrich_dicts(payloads=dict_payloads, path=path, doc_type=doc_type)

    def _enrich_blocks(
        self,
        *,
        payloads: list[ParsedBlock],
        path: Path,
        doc_type: str,
    ) -> list[ParsedBlock]:
        """Set canonical source metadata for ParsedBlock payloads."""
        enriched: list[ParsedBlock] = []
        for index, block in enumerate(payloads, start=1):
            enriched.append(
                block.model_copy(
                    update={
                        "doc_id": block.doc_id or path.stem,
                        "source_path": block.source_path or str(path),
                        "source_name": block.source_name or path.name,
                        "doc_type": block.doc_type or doc_type,
                        "page": block.page if block.page >= 1 else index,
                        "section": self._resolve_section(value=block.section),
                        "order_in_page": block.order_in_page or 1,
                    }
                )
            )
        return enriched

    def _enrich_dicts(
        self,
        *,
        payloads: list[dict[str, Any]],
        path: Path,
        doc_type: str,
    ) -> list[dict[str, Any]]:
        """Set canonical source metadata for dict payloads."""
        enriched: list[dict[str, Any]] = []
        for index, item in enumerate(payloads, start=1):
            payload = dict(item)
            payload["doc_id"] = payload.get("doc_id") or path.stem
            payload["source_path"] = payload.get("source_path") or str(path)
            payload["source_name"] = payload.get("source_name") or path.name
            payload["doc_type"] = payload.get("doc_type") or doc_type
            payload["section"] = self._resolve_section(value=payload.get("section"))
            payload["page"] = self._resolve_page(
                value=payload.get("page"), default=index
            )
            payload["order_in_page"] = payload.get("order_in_page") or 1
            enriched.append(payload)
        return enriched

    def _resolve_page(self, *, value: Any, default: int) -> int:
        """Resolve page number with safe fallback."""
        try:
            page = int(value)
        except (TypeError, ValueError):
            return default
        if page < 1:
            return default
        return page

    def _resolve_section(self, *, value: Any) -> str:
        """Normalize generic section labels into stable canonical names."""
        section = str(value or "").strip()
        if not section:
            return "Document"
        if section.lower() in {"html", "page", "unknown"}:
            return "Document"
        return section
