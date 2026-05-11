"""Confidence scoring for resolved citation metadata."""

from __future__ import annotations

from pathlib import Path

from lexrag.citation.schemas import CitationDocument
from lexrag.indexing.schemas import Chunk


class CitationConfidenceScorer:
    """Estimate how audit-ready a resolved citation is.

    The score does not claim answer faithfulness. It measures whether the
    citation carries enough metadata for a human or downstream system to trace
    the answer back to a concrete document location.
    """

    def score(
        self,
        *,
        chunk: Chunk,
        document: CitationDocument | None,
    ) -> float:
        """Score citation metadata completeness in ``[0.0, 1.0]``."""

        signals = [
            0.30,
            0.15 if chunk.metadata.page_start >= 1 else 0.0,
            0.15 if self._has_document_title(chunk=chunk, document=document) else 0.0,
            0.15
            if chunk.metadata.section_path or chunk.metadata.section_title
            else 0.0,
            0.10 if chunk.metadata.heading_anchor else 0.0,
            0.10 if chunk.metadata.source_block_ids else 0.0,
            0.05 if chunk.metadata.document_version or document else 0.0,
        ]
        return min(sum(signals), 1.0)

    def _has_document_title(
        self,
        *,
        chunk: Chunk,
        document: CitationDocument | None,
    ) -> bool:
        """Return whether the citation can present a human-readable title."""

        return bool(document and document.title) or bool(self._fallback_title(chunk))

    def _fallback_title(self, chunk: Chunk) -> str | None:
        """Infer a stable fallback title from the source path when needed."""

        if not chunk.metadata.source_path:
            return None
        return Path(chunk.metadata.source_path).stem or None
