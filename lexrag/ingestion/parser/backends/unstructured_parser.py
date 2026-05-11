"""Optional unstructured parser backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.backends.base_document_parser import BaseDocumentParser
from lexrag.ingestion.parser.builders import ParsedBlockBuilder
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class UnstructuredParser(BaseDocumentParser):
    """Broad-coverage parser used after higher-fidelity backends fail."""

    def __init__(
        self,
        *,
        block_builder: ParsedBlockBuilder | None = None,
    ) -> None:
        """Initialize shared dependencies for element normalization."""
        self.block_builder = block_builder or ParsedBlockBuilder()

    def parse(self, path: Path) -> list[ParsedBlock]:
        """Parse a document with the optional ``unstructured`` dependency.

        Args:
            path: Document path to parse.

        Returns:
            Canonical parsed blocks extracted from the document.
        """
        partition = self._load_partition_function()
        elements = partition(filename=str(path))
        return self._build_blocks(path=path, elements=elements)

    def _load_partition_function(self):
        """Load the ``unstructured`` auto-partition entry point."""
        try:
            from unstructured.partition.auto import partition
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Unstructured is not installed. Add the dependency to enable this fallback."
            ) from exc
        return partition

    def _build_blocks(self, *, path: Path, elements: list[Any]) -> list[ParsedBlock]:
        """Convert unstructured elements into canonical blocks."""
        blocks = []
        for index, element in enumerate(elements, start=1):
            text = str(element).strip()
            if not text:
                continue
            blocks.append(
                self.block_builder.build(
                    path=path,
                    parser_name=self.parser_name,
                    page=1,
                    section=f"Element {index}",
                    text=text,
                    order_in_page=index,
                    metadata={
                        "parser": self.parser_name,
                        "extraction_mode": "partition",
                    },
                )
            )
        if blocks:
            return blocks
        raise RuntimeError(f"Unstructured returned no parsed blocks for {path}")
