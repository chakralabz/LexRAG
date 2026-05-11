"""Citation resolution and post-generation validation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from lexrag.citation.citation_confidence_scorer import CitationConfidenceScorer
from lexrag.citation.citation_id_sequence import CitationIdSequence
from lexrag.citation.citation_reference_parser import CitationReferenceParser
from lexrag.citation.schemas import (
    CitationDocument,
    CitationResolutionResult,
    CitationResolverConfig,
    CitationValidationIssue,
    CitationValidationResult,
    ResolvedCitation,
)
from lexrag.indexing.schemas import Chunk


class CitationResolver:
    """Resolve retrieval chunks into citation objects and validate usage.

    The resolver owns only source traceability:

    - assigns stable citation IDs to context candidates
    - enriches citations with document and location metadata
    - validates that generated answers cite only available sources

    It does not judge semantic faithfulness; that belongs in the generation
    layer's entailment or answer-auditing components.
    """

    def __init__(
        self,
        *,
        config: CitationResolverConfig | None = None,
        reference_parser: CitationReferenceParser | None = None,
        confidence_scorer: CitationConfidenceScorer | None = None,
    ) -> None:
        self.config = config or CitationResolverConfig()
        self.reference_parser = reference_parser or CitationReferenceParser()
        self.confidence_scorer = confidence_scorer or CitationConfidenceScorer()

    def resolve(
        self,
        chunks: list[Chunk],
        *,
        document_catalog: Mapping[str, CitationDocument] | None = None,
    ) -> CitationResolutionResult:
        """Resolve context chunks into deterministic citation objects.

        Args:
            chunks: Reranked chunks selected for the generation context window.
            document_catalog: Optional document metadata keyed by ``doc_id``.

        Returns:
            A resolution result containing the citation records in the same order
            as the incoming context chunks.
        """

        self._validate_chunk_ids(chunks=chunks)
        sequence = CitationIdSequence(start=self.config.starting_citation_id)
        citations = self._build_citations(
            chunks=chunks,
            document_catalog=document_catalog or {},
            sequence=sequence,
        )
        unresolved = self._unresolved_document_ids(
            chunks=chunks,
            document_catalog=document_catalog or {},
        )
        return CitationResolutionResult(
            citations=citations,
            unresolved_document_ids=unresolved,
        )

    def validate_answer(
        self,
        answer_text: str,
        *,
        resolution: CitationResolutionResult,
    ) -> CitationValidationResult:
        """Validate generated inline citations against the resolved context."""

        references = self.reference_parser.parse(answer_text)
        resolved_ids = resolution.citation_ids()
        invalid_ids = self._invalid_ids(
            references=references, resolved_ids=resolved_ids
        )
        cited_ids = self._cited_ids(references=references, resolved_ids=resolved_ids)
        uncited_ids = sorted(resolved_ids - cited_ids)
        issues = self._build_issues(invalid_ids=invalid_ids, references=references)
        return CitationValidationResult(
            is_valid=not invalid_ids,
            references=references,
            cited_citation_ids=sorted(cited_ids),
            orphan_citation_ids=sorted(invalid_ids),
            uncited_citation_ids=uncited_ids,
            issues=issues,
        )

    def _validate_chunk_ids(self, *, chunks: list[Chunk]) -> None:
        """Reject duplicate chunk IDs before citation IDs are allocated."""

        if not self.config.require_unique_chunk_ids:
            return
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise ValueError("citation resolution requires unique chunk_ids")

    def _build_citations(
        self,
        *,
        chunks: list[Chunk],
        document_catalog: Mapping[str, CitationDocument],
        sequence: CitationIdSequence,
    ) -> list[ResolvedCitation]:
        """Materialize resolved citations in context-window order."""

        return [
            self._build_one_citation(
                chunk=chunk,
                document=self._document_for_chunk(
                    chunk=chunk, document_catalog=document_catalog
                ),
                citation_id=sequence.next_id(),
            )
            for chunk in chunks
        ]

    def _build_one_citation(
        self,
        *,
        chunk: Chunk,
        document: CitationDocument | None,
        citation_id: int,
    ) -> ResolvedCitation:
        """Build one audit-ready citation payload for a chunk."""

        return ResolvedCitation(
            citation_id=citation_id,
            document_title=self._document_title(chunk=chunk, document=document),
            document_id=chunk.metadata.doc_id,
            document_version=self._document_version(chunk=chunk, document=document),
            page=chunk.metadata.page_start,
            section=self._section_label(chunk=chunk),
            heading_anchor=chunk.metadata.heading_anchor,
            chunk_id=chunk.chunk_id,
            source_block_ids=tuple(chunk.metadata.source_block_ids),
            confidence=self.confidence_scorer.score(chunk=chunk, document=document),
        )

    def _document_for_chunk(
        self,
        *,
        chunk: Chunk,
        document_catalog: Mapping[str, CitationDocument],
    ) -> CitationDocument | None:
        """Look up document metadata without coupling the resolver to storage."""

        if not chunk.metadata.doc_id:
            return None
        return document_catalog.get(chunk.metadata.doc_id)

    def _document_title(
        self,
        *,
        chunk: Chunk,
        document: CitationDocument | None,
    ) -> str:
        """Resolve the human-readable title shown to operators and users."""

        if document and document.title:
            return document.title
        if chunk.metadata.source_path:
            return Path(chunk.metadata.source_path).stem or chunk.chunk_id
        return chunk.metadata.doc_id or chunk.chunk_id

    def _document_version(
        self,
        *,
        chunk: Chunk,
        document: CitationDocument | None,
    ) -> str | None:
        """Prefer catalog metadata but preserve chunk-local fallback values."""

        if document and document.version:
            return document.version
        return chunk.metadata.document_version

    def _section_label(self, *, chunk: Chunk) -> str | None:
        """Build the most descriptive available section label."""

        if chunk.metadata.section_path:
            return " > ".join(chunk.metadata.section_path)
        return chunk.metadata.section_title

    def _unresolved_document_ids(
        self,
        *,
        chunks: list[Chunk],
        document_catalog: Mapping[str, CitationDocument],
    ) -> list[str]:
        """Report which chunk document IDs lacked catalog metadata."""

        unresolved = {
            chunk.metadata.doc_id
            for chunk in chunks
            if chunk.metadata.doc_id and chunk.metadata.doc_id not in document_catalog
        }
        return sorted(unresolved)

    def _invalid_ids(self, *, references, resolved_ids: set[int]) -> set[int]:
        """Return cited IDs that are not present in the context window."""

        return {reference.citation_id for reference in references} - resolved_ids

    def _cited_ids(self, *, references, resolved_ids: set[int]) -> set[int]:
        """Return cited IDs that successfully map to resolved sources."""

        return {reference.citation_id for reference in references} & resolved_ids

    def _build_issues(
        self,
        *,
        invalid_ids: set[int],
        references,
    ) -> list[CitationValidationIssue]:
        """Create actionable validation issues for orphan citations."""

        issues = []
        for reference in references:
            if reference.citation_id not in invalid_ids:
                continue
            issues.append(
                CitationValidationIssue(
                    code="orphan_citation_id",
                    message="Generated answer cited a source that was not in context.",
                    citation_id=reference.citation_id,
                    raw_text=reference.raw_text,
                )
            )
        return issues
