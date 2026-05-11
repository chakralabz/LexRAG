"""Format ordered context sources into a prompt-safe window."""

from __future__ import annotations

from lexrag.context_builder.schemas import (
    ContextBuilderConfig,
    ContextSource,
    ContextWindow,
)


class ContextPromptFormatter:
    """Render the final context window with explicit source headers."""

    def __init__(self, *, config: ContextBuilderConfig | None = None) -> None:
        self.config = config or ContextBuilderConfig()

    def format(
        self,
        *,
        query: str,
        sources: list[ContextSource],
        warnings: list[str],
    ) -> ContextWindow:
        """Build the generation-ready context window contract."""

        blocks = [
            self._header(source=source) + "\n" + source.chunk.text for source in sources
        ]
        if warnings:
            blocks.insert(0, self._warning_block(warnings=warnings))
        formatted = "\n\n".join(blocks).strip()
        return ContextWindow(
            query=query,
            formatted_context=formatted,
            sources=sources,
            total_tokens=sum(source.token_count for source in sources),
            num_sources=len(sources),
            num_documents=len(
                {
                    source.citation.document_id
                    for source in sources
                    if source.citation.document_id
                }
            ),
            conflict_detected=bool(warnings),
            context_quality_score=self._quality_score(sources=sources),
            warnings=warnings,
        )

    def _header(self, *, source: ContextSource) -> str:
        """Render one architecture-compliant source header."""

        section = source.citation.section or "Unknown section"
        return (
            f"[SOURCE {source.citation.citation_id} | "
            f"doc: {source.citation.document_title} | "
            f"page {source.citation.page} | "
            f"section: {section}]"
        )

    def _warning_block(self, *, warnings: list[str]) -> str:
        """Place conflict instructions at the top of the prompt context."""

        body = "\n".join(f"- {warning}" for warning in warnings)
        return "[CONFLICT WARNING]\n" + body

    def _quality_score(self, *, sources: list[ContextSource]) -> float:
        """Average per-source quality, falling back to zero on empty context."""

        if not sources:
            return 0.0
        return sum(source.quality_score for source in sources) / len(sources)
