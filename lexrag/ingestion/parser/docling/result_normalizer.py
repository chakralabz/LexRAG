"""Normalize Docling conversion output into canonical parsed blocks.

Docling can return rich item streams, markdown exports, or plain text depending
on the document and the enabled pipeline features. This normalizer chooses the
best available representation in a stable order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexrag.ingestion.parser.builders import ParsedBlockBuilder
from lexrag.ingestion.parser.schemas.parsed_block import ParsedBlock


class DoclingResultNormalizer:
    """Convert Docling results into LexRAG parsed blocks."""

    def __init__(self, *, block_builder: ParsedBlockBuilder | None = None) -> None:
        self.block_builder = block_builder or ParsedBlockBuilder()

    def normalize(
        self,
        *,
        result: Any,
        path: Path,
        parser_name: str,
    ) -> list[ParsedBlock]:
        """Choose the highest-fidelity output representation available.

        Preference order matters:
        1. structured items preserve the most semantic signal
        2. markdown preserves some structure when items are unavailable
        3. page/text fallback ensures the document is still parseable
        """
        document = self._resolve_document(result=result, path=path)
        defaults = self._build_defaults(path=path, parser_name=parser_name)
        blocks = self._extract_structured(
            document=document, path=path, defaults=defaults, parser_name=parser_name
        )
        if blocks:
            return blocks
        content = self._extract_content(document=document, path=path)
        blocks = self._extract_markdown_sections(
            content=content,
            path=path,
            defaults=defaults,
            parser_name=parser_name,
        )
        if blocks:
            return blocks
        return self._extract_page_fallback(
            content=content,
            path=path,
            defaults=defaults,
            parser_name=parser_name,
        )

    def _resolve_document(self, *, result: Any, path: Path) -> Any:
        """Extract the Docling document object from the conversion result."""
        if hasattr(result, "document"):
            return result.document
        raise RuntimeError(f"No parsed document returned by Docling for {path}")

    def _build_defaults(self, *, path: Path, parser_name: str) -> dict[str, Any]:
        """Build shared metadata that every Docling-derived block should carry."""
        return {
            "doc_id": path.stem,
            "source_path": str(path),
            "source_name": path.name,
            "doc_type": path.suffix.lower().lstrip(".") or None,
            "parser_used": parser_name,
            "ocr_used": "docling_ocr",
        }

    def _extract_structured(
        self,
        *,
        document: Any,
        path: Path,
        defaults: dict[str, Any],
        parser_name: str,
    ) -> list[ParsedBlock]:
        """Extract the richest available item-level blocks from Docling output."""
        if not hasattr(document, "iterate_items"):
            return []
        blocks: list[ParsedBlock] = []
        order = 0
        try:
            for item, _level in document.iterate_items():
                text = self._resolve_item_text(item=item)
                if not text:
                    continue
                order += 1
                blocks.append(
                    self._build_structured_block(
                        path=path,
                        defaults=defaults,
                        item=item,
                        order=order,
                        text=text,
                        parser_name=parser_name,
                    )
                )
        except Exception:
            # Structured extraction is best-effort. If Docling exposes a
            # partially incompatible item API, we gracefully fall back instead
            # of failing the whole document.
            return []
        return blocks

    def _build_structured_block(
        self,
        *,
        path: Path,
        defaults: dict[str, Any],
        item: Any,
        order: int,
        text: str,
        parser_name: str,
    ) -> ParsedBlock:
        """Build one canonical parsed block from one Docling item."""
        provenance = self._primary_provenance(item=item)
        # Markdown is often richer than plain text for tables and captions, so
        # we keep it when available while still deriving `text` separately.
        markdown = self._resolve_item_markdown(item=item) or text
        page = self._resolve_page_number(
            value=self._resolve_page_value(item=item, provenance=provenance)
        )
        block_type = self._detect_block_type(item=item, text=text)
        confidence = self._resolve_confidence(value=getattr(item, "confidence", None))
        block = self.block_builder.build(
            path=path,
            parser_name=parser_name,
            page=page,
            section=self._resolve_section(item=item, text=text),
            heading_level=self._resolve_heading_level(item=item),
            block_type=block_type,
            text=text,
            markdown=markdown,
            bbox=self._resolve_bbox(item=item, provenance=provenance),
            order_in_page=order,
            is_ocr=self._resolve_item_bool(
                item=item,
                names=("is_ocr", "ocr_used", "used_ocr"),
            ),
            confidence=confidence,
            ocr_used="docling_ocr",
            parse_confidence=confidence,
            metadata=self._structured_metadata(item=item, block_type=block_type),
        )
        return block.model_copy(update=defaults)

    def _resolve_item_text(self, *, item: Any) -> str:
        """Prefer native text and fall back to markdown-like item rendering."""
        text = str(getattr(item, "text", "")).strip()
        if text:
            return text
        markdown = self._resolve_item_markdown(item=item)
        return markdown or ""

    def _resolve_item_markdown(self, *, item: Any) -> str | None:
        """Read markdown from Docling's optional item export APIs."""
        for name in ("export_to_markdown", "to_markdown"):
            value = getattr(item, name, None)
            if callable(value):
                rendered = self._safe_render_markdown(render=value)
                if rendered:
                    return rendered
        for name in ("markdown", "md"):
            value = getattr(item, name, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _safe_render_markdown(self, *, render: Any) -> str | None:
        """Call optional markdown exporters without breaking the parse flow."""
        try:
            rendered = render()
        except Exception:
            return None
        if not isinstance(rendered, str):
            return None
        cleaned = rendered.strip()
        return cleaned or None

    def _primary_provenance(self, *, item: Any) -> Any | None:
        """Return the first provenance record when multiple are attached."""
        provenance = getattr(item, "prov", None)
        if isinstance(provenance, list) and provenance:
            return provenance[0]
        return None

    def _resolve_page_value(self, *, item: Any, provenance: Any | None) -> Any:
        """Resolve page number from direct item fields or provenance fallback."""
        direct_page = getattr(item, "page_no", None)
        if direct_page is not None:
            return direct_page
        if provenance is not None:
            return getattr(provenance, "page_no", 1)
        return 1

    def _resolve_bbox(
        self,
        *,
        item: Any,
        provenance: Any | None,
    ) -> tuple[float, float, float, float] | None:
        """Resolve bbox from direct item fields, then provenance if needed."""
        bbox = self._normalize_bbox(value=getattr(item, "bbox", None))
        if bbox is not None:
            return bbox
        if provenance is None:
            return None
        return self._normalize_bbox(value=getattr(provenance, "bbox", None))

    def _extract_content(self, *, document: Any, path: Path) -> str:
        """Try progressively weaker document-wide content representations."""
        for extractor in (
            self._try_markdown,
            self._try_plain_text,
            self._try_generic_repr,
        ):
            content = extractor(document=document)
            if content:
                return content
        raise RuntimeError(f"Docling returned empty content for {path}")

    def _try_markdown(self, *, document: Any) -> str:
        """Export full-document markdown when the backend supports it."""
        if not hasattr(document, "export_to_markdown"):
            return ""
        try:
            return str(document.export_to_markdown()).strip()
        except Exception:
            return ""

    def _try_plain_text(self, *, document: Any) -> str:
        """Export full-document plain text as the next best fallback."""
        if not hasattr(document, "text"):
            return ""
        try:
            return str(document.text).strip()
        except Exception:
            return ""

    def _try_generic_repr(self, *, document: Any) -> str:
        """Last-resort fallback when Docling exposes no dedicated text export."""
        try:
            return str(document).strip()
        except Exception:
            return ""

    def _extract_markdown_sections(
        self,
        *,
        content: str,
        path: Path,
        defaults: dict[str, Any],
        parser_name: str,
    ) -> list[ParsedBlock]:
        """Split markdown into coarse sections when structured items are absent."""
        sections = [part.strip() for part in content.split("\n## ") if part.strip()]
        return [
            self.block_builder.build(
                path=path,
                parser_name=parser_name,
                page=index,
                section=f"Section {index}",
                heading_level=2,
                block_type="section",
                text=section,
                markdown=section,
                order_in_page=1,
                ocr_used="docling_ocr",
                metadata={
                    "parser": parser_name,
                    "extraction_mode": "markdown_fallback",
                },
            ).model_copy(update=defaults)
            for index, section in enumerate(sections, start=1)
        ]

    def _extract_page_fallback(
        self,
        *,
        content: str,
        path: Path,
        defaults: dict[str, Any],
        parser_name: str,
    ) -> list[ParsedBlock]:
        """Split plain text into page-like blocks using form-feed markers."""
        chunks = [part.strip() for part in content.split("\f") if part.strip()]
        return [
            self.block_builder.build(
                path=path,
                parser_name=parser_name,
                page=index,
                section=f"Page {index}",
                text=chunk,
                markdown=chunk,
                order_in_page=1,
                ocr_used="docling_ocr",
                metadata={
                    "parser": parser_name,
                    "extraction_mode": "page_fallback",
                },
            ).model_copy(update=defaults)
            for index, chunk in enumerate(chunks or [content], start=1)
        ]

    def _resolve_page_number(self, *, value: Any) -> int:
        """Normalize page numbers into safe positive integers."""
        try:
            resolved = int(value)
        except (TypeError, ValueError):
            return 1
        return max(resolved, 1)

    def _resolve_confidence(self, *, value: Any) -> float | None:
        """Normalize backend confidence values into ``[0.0, 1.0]``."""
        try:
            if value is None:
                return None
            resolved = float(value)
        except (TypeError, ValueError):
            return None
        return min(max(resolved, 0.0), 1.0)

    def _resolve_heading_level(self, *, item: Any) -> int | None:
        """Parse heading levels when Docling provides them."""
        raw = getattr(item, "level", None)
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    def _resolve_section(self, *, item: Any, text: str) -> str:
        """Choose a readable section label for downstream debugging and UI."""
        label = str(getattr(item, "label", "")).strip().lower()
        if label == "title":
            return "Title"
        if label.startswith("heading"):
            return text.splitlines()[0][:120] or "Heading"
        if label:
            return label.replace("_", " ").title()
        return text.splitlines()[0][:120] or "Block"

    def _resolve_item_bool(self, *, item: Any, names: tuple[str, ...]) -> bool:
        """Read a boolean flag from several backend-specific field names."""
        for name in names:
            value = getattr(item, name, None)
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and value.strip():
                return value.lower() in {"1", "true", "yes"}
        return False

    def _structured_metadata(self, *, item: Any, block_type: str) -> dict[str, Any]:
        """Build structured metadata used by chunking and diagnostics."""
        label = str(getattr(item, "label", "")).strip() or None
        visual_block = block_type in {"table", "table_caption", "image_caption"}
        return {
            "parser": "docling",
            "label": label,
            "block_type": block_type,
            "extraction_mode": "structured",
            "visual_block": visual_block,
        }

    def _detect_block_type(self, *, item: Any, text: str) -> str:
        """Map Docling item labels into LexRAG's smaller block taxonomy."""
        label = str(getattr(item, "label", "")).strip().lower()
        if label == "table":
            return "table"
        if label == "caption":
            return self._caption_type(text=text)
        if label in {"title", "heading", "subtitle"}:
            return "heading"
        if label == "list_item":
            return "list_item"
        return "paragraph"

    def _caption_type(self, *, text: str) -> str:
        """Differentiate figure captions from table captions using prefixes."""
        lowered = text.lower()
        if lowered.startswith("table "):
            return "table_caption"
        if lowered.startswith("figure "):
            return "image_caption"
        return "caption"

    def _normalize_bbox(
        self,
        *,
        value: Any,
    ) -> tuple[float, float, float, float] | None:
        """Normalize tuple- or object-style bounding boxes into one shape."""
        if value is None:
            return None
        if isinstance(value, tuple) and len(value) == 4:
            return tuple(float(item) for item in value)
        names = (
            ("left", "top", "right", "bottom"),
            ("l", "t", "r", "b"),
        )
        for left_name, top_name, right_name, bottom_name in names:
            # Docling and provenance objects do not always agree on coordinate
            # attribute names, so we support both verbose and short variants.
            if all(hasattr(value, name) for name in (left_name, top_name, right_name, bottom_name)):
                return (
                    float(getattr(value, left_name)),
                    float(getattr(value, top_name)),
                    float(getattr(value, right_name)),
                    float(getattr(value, bottom_name)),
                )
        return None
