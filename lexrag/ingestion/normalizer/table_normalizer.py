"""Normalization stage for table blocks."""

from __future__ import annotations

import re

from lexrag.ingestion.normalizer.base_normalizer import BaseNormalizer
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock

_MULTI_SPACES = re.compile(r"[ \t]{2,}")


class TableNormalizer(BaseNormalizer):
    """Preserves table structure in a retrieval-safe markdown form.

    The parser output for tables is often inconsistent, but flattening tables to
    prose destroys the row and column relationships retrieval depends on. This
    stage normalizes tables into a stable markdown representation and emits
    repair metadata for auditability.
    """

    def normalize(self, block: ParsedBlock) -> ParsedBlock:
        """Normalizes table rows while preserving their structural intent.

        Args:
            block: Parsed block candidate.

        Returns:
            Updated block when it represents table content.
        """
        if block.block_type != "table":
            return block
        source = (block.markdown or block.text or "").strip()
        if not source:
            return block
        rows = self._parse_rows(source)
        if not rows:
            return block
        padded_rows, merged_cells_suspected = self._pad_rows(rows)
        markdown = self._render_markdown_table(padded_rows)
        metadata = dict(block.metadata)
        metadata["table_row_count"] = len(padded_rows)
        metadata["table_column_count"] = len(padded_rows[0]) if padded_rows else 0
        metadata["table_merged_cells_suspected"] = merged_cells_suspected
        metadata["protected"] = True
        return block.model_copy(
            update={"text": markdown, "markdown": markdown, "metadata": metadata}
        )

    def _parse_rows(self, source: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for raw_line in source.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            stripped_line = raw_line.strip()
            if not stripped_line:
                continue
            rows.append(self._split_row(stripped_line))
        return rows

    def _split_row(self, row: str) -> list[str]:
        if "|" in row:
            cells = row.strip("|").split("|")
        elif "\t" in row:
            cells = row.split("\t")
        else:
            cells = [row]
        return [self._clean_cell(cell) for cell in cells]

    def _clean_cell(self, cell: str) -> str:
        return _MULTI_SPACES.sub(" ", cell).strip()

    def _pad_rows(self, rows: list[list[str]]) -> tuple[list[list[str]], bool]:
        max_columns = max(len(row) for row in rows)
        merged_cells_suspected = any(len(row) != max_columns for row in rows)
        padded_rows = [row + ([""] * (max_columns - len(row))) for row in rows]
        return padded_rows, merged_cells_suspected

    def _render_markdown_table(self, rows: list[list[str]]) -> str:
        if len(rows) == 1:
            return self._render_row(rows[0])
        header = self._render_row(rows[0])
        divider = self._render_row(["---"] * len(rows[0]))
        body = [self._render_row(row) for row in rows[1:]]
        return "\n".join([header, divider, *body])

    def _render_row(self, row: list[str]) -> str:
        return "| " + " | ".join(row) + " |"
