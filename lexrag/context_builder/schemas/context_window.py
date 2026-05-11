"""Generation-ready context window contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lexrag.citation.schemas import CitationResolutionResult
from lexrag.context_builder.schemas.context_source import ContextSource


class ContextWindow(BaseModel):
    """Stores the final prompt context plus observability metadata.

    Attributes:
        query: Original user question that this context answers.
        formatted_context: Prompt-safe rendered source window.
        sources: Ordered citation-linked sources retained after compression.
        total_tokens: Estimated tokens consumed by retained source text.
        num_sources: Number of retained sources.
        num_documents: Number of distinct documents represented.
        conflict_detected: Whether the builder found conflicting evidence.
        context_quality_score: Aggregate quality signal for the final window.
        warnings: Human-readable prompt warnings such as detected conflicts.
    """

    model_config = ConfigDict(frozen=True)

    query: str = Field(min_length=1)
    formatted_context: str = Field(default="")
    sources: list[ContextSource] = Field(default_factory=list)
    total_tokens: int = Field(ge=0)
    num_sources: int = Field(ge=0)
    num_documents: int = Field(ge=0)
    conflict_detected: bool
    context_quality_score: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)

    def to_citation_resolution(self) -> CitationResolutionResult:
        """Project the prompt sources back to the citation-validation contract."""

        return CitationResolutionResult(
            citations=[source.citation for source in self.sources],
            unresolved_document_ids=[],
        )
