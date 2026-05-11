"""Post-processing for canonical chunks before they leave the chunking layer."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.chunker.schemas.chunk_metadata import ChunkMetadata
from lexrag.ingestion.chunker.schemas.chunking_config import ChunkingConfig
from lexrag.ingestion.chunker.tokenization_engine import TokenizationEngine


class ChunkPostProcessor:
    """Validate and enrich chunks before the embedding preparation layer.

    This is the last architecture-defined checkpoint before embedding text is
    constructed. It centralizes quality scoring, overlap wiring, and metadata
    enrichment so the builder can stay focused on segmentation concerns.
    """

    def __init__(
        self,
        *,
        config: ChunkingConfig,
        tokenization_engine: TokenizationEngine | None = None,
    ) -> None:
        self.config = config
        self.tokenization_engine = tokenization_engine or TokenizationEngine()

    def process(self, chunks: list[Chunk]) -> list[Chunk]:
        """Enrich chunk metadata with adjacency links and quality signals.

        Args:
            chunks: Canonical chunks for a single document.

        Returns:
            Post-processed chunks with stable adjacency and risk annotations.
        """
        processed: list[Chunk] = []
        for index, chunk in enumerate(chunks):
            previous_chunk = chunks[index - 1] if index > 0 else None
            next_chunk = chunks[index + 1] if index < len(chunks) - 1 else None
            metadata = self._build_metadata(
                chunk=chunk,
                previous_chunk=previous_chunk,
                next_chunk=next_chunk,
            )
            processed.append(chunk.model_copy(update={"metadata": metadata}))
        return processed

    def _build_metadata(
        self,
        *,
        chunk: Chunk,
        previous_chunk: Chunk | None,
        next_chunk: Chunk | None,
    ) -> ChunkMetadata:
        """Copies metadata while wiring adjacency and computed quality fields."""
        payload = chunk.metadata.model_dump()
        overlap_prev = self._has_textual_overlap(
            previous_chunk=previous_chunk,
            current_chunk=chunk,
        )
        overlap_next = self._has_textual_overlap(
            previous_chunk=chunk,
            current_chunk=next_chunk,
        )
        payload["previous_chunk_id"] = (
            previous_chunk.chunk_id if previous_chunk else None
        )
        payload["next_chunk_id"] = next_chunk.chunk_id if next_chunk else None
        payload["overlap_prev"] = overlap_prev
        payload["overlap_next"] = overlap_next
        payload["chunk_quality_score"] = self._quality_score(metadata=chunk.metadata)
        payload["metadata"] = self._enriched_metadata(
            chunk=chunk,
            previous_chunk=previous_chunk,
            next_chunk=next_chunk,
            quality_score=payload["chunk_quality_score"],
        )
        return ChunkMetadata.model_validate(payload)

    def _has_textual_overlap(
        self,
        *,
        previous_chunk: Chunk | None,
        current_chunk: Chunk | None,
    ) -> bool:
        """Return whether adjacent chunks share an exact token boundary."""
        if previous_chunk is None or current_chunk is None:
            return False
        previous_tokens = self.tokenization_engine.tokenize(previous_chunk.text)
        current_tokens = self.tokenization_engine.tokenize(current_chunk.text)
        limit = min(
            len(previous_tokens),
            len(current_tokens),
            max(self.config.overlap_tokens, 1),
        )
        for size in range(limit, 0, -1):
            if previous_tokens[-size:] == current_tokens[:size]:
                return True
        return False

    def _enriched_metadata(
        self,
        *,
        chunk: Chunk,
        previous_chunk: Chunk | None,
        next_chunk: Chunk | None,
        quality_score: float,
    ) -> dict[str, object]:
        """Build extension metadata needed by downstream retrieval layers."""
        metadata = dict(chunk.metadata.metadata)
        metadata["quality_flags"] = self._quality_flags(
            chunk=chunk, quality_score=quality_score
        )
        metadata["citation_validation"] = self._citation_validation(chunk=chunk)
        metadata["reranker_metadata"] = self._reranker_metadata(chunk=chunk)
        metadata["hallucination_risk"] = self._hallucination_risk(chunk=chunk)
        metadata["overlap_validation"] = self._overlap_validation(
            previous_chunk=previous_chunk,
            current_chunk=chunk,
            next_chunk=next_chunk,
        )
        metadata["final_normalized_text"] = self._final_normalized_text(chunk.text)
        return metadata

    def _quality_score(self, *, metadata: ChunkMetadata) -> float:
        """Computes a bounded chunk quality score from architecture signals."""
        parse_score = metadata.parse_confidence or metadata.avg_confidence or 0.7
        heading_score = 1.0 if metadata.heading_anchor else 0.0
        token_score = self._token_budget_score(metadata=metadata)
        section_score = 1.0 if metadata.section_path else 0.0
        ocr_score = 0.0 if metadata.contains_ocr else 1.0
        score = (
            (0.30 * parse_score)
            + (0.20 * heading_score)
            + (0.20 * token_score)
            + (0.15 * section_score)
            + (0.15 * ocr_score)
        )
        return round(min(max(score, 0.0), 1.0), 4)

    def _token_budget_score(self, *, metadata: ChunkMetadata) -> float:
        """Rewards chunks that land within the configured size envelope."""
        count = metadata.token_count or 0
        if self.config.min_chunk_tokens <= count <= self.config.max_chunk_tokens:
            return 1.0
        if 0 < count < self.config.min_chunk_tokens:
            return round(count / self.config.min_chunk_tokens, 4)
        if count > self.config.max_chunk_tokens:
            return round(self.config.max_chunk_tokens / count, 4)
        return 0.0

    def _quality_flags(self, *, chunk: Chunk, quality_score: float) -> list[str]:
        """Build quality flags that downstream systems can reason about."""
        flags: list[str] = []
        if quality_score < self.config.low_quality_threshold:
            flags.append("low_quality")
        if (
            chunk.metadata.parse_confidence is not None
            and chunk.metadata.parse_confidence
            < self.config.low_confidence_parse_threshold
        ):
            flags.append("low_parse_confidence")
        confidence = chunk.metadata.avg_confidence or 0.0
        if (
            chunk.metadata.contains_ocr
            and confidence < self.config.low_confidence_ocr_threshold
        ):
            flags.append("high_ocr_risk")
        if self._citation_validation(chunk=chunk)["out_of_bounds"]:
            flags.append("citation_out_of_bounds")
        return flags

    def _citation_validation(self, *, chunk: Chunk) -> dict[str, object]:
        """Inspect simple citation patterns and validate page-local references."""
        references = self._page_references(text=chunk.text)
        page_start = chunk.metadata.page_start
        page_end = chunk.metadata.page_end
        invalid = [page for page in references if page < page_start or page > page_end]
        return {
            "references": references,
            "out_of_bounds": bool(invalid),
            "invalid_references": invalid,
        }

    def _page_references(self, *, text: str) -> list[int]:
        """Extract page references from chunk text using conservative patterns."""
        references: list[int] = []
        for part in text.replace(",", " ").split():
            lowered = part.lower().strip("[]().:")
            if lowered.startswith("p.") and lowered[2:].isdigit():
                references.append(int(lowered[2:]))
            if lowered.startswith("page") and lowered[4:].isdigit():
                references.append(int(lowered[4:]))
        return references

    def _reranker_metadata(self, *, chunk: Chunk) -> dict[str, object]:
        """Add compact metadata that rerankers and debuggers can reuse cheaply."""
        section_path = " > ".join(chunk.metadata.section_path)
        title = chunk.metadata.section_title or section_path or chunk.metadata.doc_id
        return {
            "doc_title": chunk.metadata.doc_id or "unknown_doc",
            "section_summary": title or "Untitled Section",
            "block_type_distribution": {
                chunk.metadata.chunk_type: len(chunk.metadata.source_block_ids)
            },
        }

    def _hallucination_risk(self, *, chunk: Chunk) -> dict[str, object]:
        """Summarize chunk-level grounding risk for downstream answer logic."""
        parse_confidence = chunk.metadata.parse_confidence
        ocr_confidence = chunk.metadata.avg_confidence
        high_risk = False
        reasons: list[str] = []
        if (
            parse_confidence is not None
            and parse_confidence < self.config.low_confidence_parse_threshold
        ):
            high_risk = True
            reasons.append("low_parse_confidence")
        if (
            chunk.metadata.contains_ocr
            and (ocr_confidence or 0.0) < self.config.low_confidence_ocr_threshold
        ):
            high_risk = True
            reasons.append("low_ocr_confidence")
        return {"high_risk": high_risk, "reasons": reasons}

    def _overlap_validation(
        self,
        *,
        previous_chunk: Chunk | None,
        current_chunk: Chunk,
        next_chunk: Chunk | None,
    ) -> dict[str, object]:
        """Validate adjacency references now that stable chunk IDs exist."""
        return {
            "previous_exists": previous_chunk is not None,
            "next_exists": next_chunk is not None,
            "expected_previous_chunk_id": previous_chunk.chunk_id
            if previous_chunk
            else None,
            "expected_next_chunk_id": next_chunk.chunk_id if next_chunk else None,
            "token_count": current_chunk.metadata.token_count,
        }

    def _final_normalized_text(self, text: str) -> str:
        """Apply the last whitespace cleanup before embedding text is derived."""
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(line for line in lines if line.strip() or line == "")
