"""Production citation-resolution package.

This package owns the narrow boundary between retrieval/reranking and the
generation context builder. It resolves retrieval-ready chunks into stable
source references and validates inline citation usage after generation without
reaching backward into indexing or forward into answer synthesis.
"""

from lexrag.citation.citation_confidence_scorer import CitationConfidenceScorer
from lexrag.citation.citation_id_sequence import CitationIdSequence
from lexrag.citation.citation_reference_parser import CitationReferenceParser
from lexrag.citation.citation_resolver import CitationResolver
from lexrag.citation.schemas import (
    CitationDocument,
    CitationReference,
    CitationResolutionResult,
    CitationResolverConfig,
    CitationValidationIssue,
    CitationValidationResult,
    ResolvedCitation,
)

__all__ = [
    "CitationConfidenceScorer",
    "CitationDocument",
    "CitationIdSequence",
    "CitationReference",
    "CitationReferenceParser",
    "CitationResolutionResult",
    "CitationResolver",
    "CitationResolverConfig",
    "CitationValidationIssue",
    "CitationValidationResult",
    "ResolvedCitation",
]
