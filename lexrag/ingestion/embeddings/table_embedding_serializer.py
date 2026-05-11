"""Table-aware serialization utilities for embedding preparation."""

from __future__ import annotations


class TableEmbeddingSerializer:
    """Serialize table text into a retrieval-friendly representation."""

    def __init__(self, *, row_limit: int = 32) -> None:
        self.row_limit = row_limit

    def serialize(self, *, text: str, heading: str | None) -> str:
        """Convert table-like text into a normalized embedding payload."""
        rows = self._rows(text=text)
        prefix = f"[TABLE: {heading}]" if heading else "[TABLE]"
        if not rows:
            return f"{prefix}\n{text.strip()}".strip()
        body = "\n".join(rows[: self.row_limit])
        return f"{prefix}\n{body}".strip()

    def _rows(self, *, text: str) -> list[str]:
        """Normalize table rows while keeping simple row/value structure."""
        rows: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip().strip("|")
            if not cleaned:
                continue
            if set(cleaned) <= {"-", ":"}:
                continue
            cells = [cell.strip() for cell in cleaned.split("|") if cell.strip()]
            if not cells:
                continue
            rows.append(" ; ".join(cells))
        return rows
