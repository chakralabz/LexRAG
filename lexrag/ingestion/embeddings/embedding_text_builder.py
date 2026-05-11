"""Build embedding text from canonical chunks."""

from __future__ import annotations

from lexrag.ingestion.chunker.schemas.chunk import Chunk
from lexrag.ingestion.embeddings.schemas.embedding_preparation_config import (
    EmbeddingPreparationConfig,
)
from lexrag.ingestion.embeddings.table_embedding_serializer import (
    TableEmbeddingSerializer,
)


class EmbeddingTextBuilder:
    """Create retrieval-optimized embedding text for each chunk."""

    def __init__(
        self,
        *,
        config: EmbeddingPreparationConfig | None = None,
        table_serializer: TableEmbeddingSerializer | None = None,
    ) -> None:
        self.config = config or EmbeddingPreparationConfig()
        self.table_serializer = table_serializer or TableEmbeddingSerializer(
            row_limit=self.config.table_row_limit
        )

    def build(self, *, chunk: Chunk) -> str:
        """Build embedding text for a canonical chunk."""
        if chunk.metadata.chunk_type == "table":
            return self.table_serializer.serialize(
                text=chunk.text,
                heading=self._context_label(chunk=chunk),
            )
        if chunk.metadata.chunk_type == "code":
            return self._code_text(chunk=chunk)
        if chunk.metadata.chunk_type == "list":
            return self._list_text(chunk=chunk)
        return self._paragraph_text(chunk=chunk)

    def _paragraph_text(self, *, chunk: Chunk) -> str:
        """Build paragraph embedding text with heading and section context."""
        label = self._context_label(chunk=chunk)
        if label:
            return f"[HEADING: {label}] {chunk.text}".strip()
        return chunk.text.strip()

    def _code_text(self, *, chunk: Chunk) -> str:
        """Build code embedding text while preserving language hints."""
        language = chunk.metadata.metadata.get("code_language")
        prefix = f"[CODE: {language}]" if isinstance(language, str) else "[CODE]"
        return f"{prefix}\n{chunk.text}".strip()

    def _list_text(self, *, chunk: Chunk) -> str:
        """Build list embedding text with section anchor context."""
        label = self._context_label(chunk=chunk)
        prefix = f"[SECTION: {label}]" if label else "[SECTION]"
        return f"{prefix}\n{chunk.text}".strip()

    def _context_label(self, *, chunk: Chunk) -> str | None:
        """Resolve the most useful contextual label for embedding text."""
        if self.config.include_heading_context and chunk.metadata.heading_anchor:
            return chunk.metadata.heading_anchor
        if self.config.include_section_context and chunk.metadata.section_path:
            return " > ".join(chunk.metadata.section_path)
        return chunk.metadata.section_title
