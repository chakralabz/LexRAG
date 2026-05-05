"""Parser confidence scoring aligned with the architecture document.

The scoring intentionally uses simple, explainable heuristics. It is meant for
auditability and downstream debugging, not as a learned quality model.
"""

from __future__ import annotations

from lexrag.ingestion.parser.schemas.parse_attempt import ParseAttempt
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock
from lexrag.ingestion.parser.schemas.parser_selection import ParserSelection


class ParseConfidenceScorer:
    """Compute parser confidence from route decisions and output signals."""

    def score(
        self,
        *,
        selection: ParserSelection,
        attempts: list[ParseAttempt],
        blocks: list[ParsedBlock],
    ) -> float:
        """Compute a stable parse confidence score in ``[0.0, 1.0]``.

        Args:
            selection: Parser route chosen for the document.
            attempts: Backend execution attempts.
            blocks: Successfully extracted parsed blocks.

        Returns:
            Confidence score for downstream audit and quality signals.
        """
        score = 0.3
        # Non-OCR routes generally preserve more native structure and therefore
        # start with a stronger confidence prior.
        if not selection.requires_ocr:
            score += 0.4
        # Tables and heading levels are crude but useful indicators that the
        # parser preserved structure instead of flattening everything to text.
        if any(block.block_type == "table" for block in blocks):
            score += 0.2
        if any(block.heading_level is not None for block in blocks):
            score += 0.2
        # OCR and fallback are both reliability penalties because they usually
        # imply weaker structural fidelity or an upstream parse failure.
        if selection.requires_ocr:
            score -= 0.3
        if self._used_fallback(selection=selection, attempts=attempts):
            score -= 0.2
        return max(0.0, min(1.0, score))

    def _used_fallback(
        self,
        *,
        selection: ParserSelection,
        attempts: list[ParseAttempt],
    ) -> bool:
        """Return whether a non-primary parser produced the final result."""
        successful = next((attempt for attempt in attempts if attempt.succeeded), None)
        if successful is None:
            return True
        return successful.parser_name != selection.primary_parser_name
