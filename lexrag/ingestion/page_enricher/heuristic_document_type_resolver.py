"""Heuristic document type resolver."""

from __future__ import annotations

from pathlib import Path


class HeuristicDocumentTypeResolver:
    """Infer document type from source path tokens."""

    def resolve(self, *, path: Path) -> str:
        """Resolve a stable doc_type for known corpus families."""
        normalized = str(path).lower()
        if "10-k" in normalized or "/sec/" in normalized or "sec_" in normalized:
            return "sec_filing"
        if "court" in normalized or "opinion" in normalized:
            return "court_opinion"
        if "eur-lex" in normalized or "ai_act" in normalized:
            return "regulation"
        if "arxiv" in normalized:
            return "research_paper"
        suffix = path.suffix.lower()
        if suffix in {".html", ".htm"}:
            return "web_document"
        if suffix == ".pdf":
            return "pdf_document"
        return "unknown"
