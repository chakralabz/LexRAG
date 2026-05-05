"""Recursive splitter for oversized blocks."""

from __future__ import annotations

from lexrag.ingestion.chunker.support.tokenization_engine import TokenizationEngine


class RecursiveTextSplitter:
    """Split oversized text using semantic separators before token windows."""

    def __init__(
        self,
        *,
        tokenization_engine: TokenizationEngine | None = None,
        separators: tuple[str, ...],
        min_tokens: int,
        target_tokens: int,
        max_tokens: int,
        overlap_tokens: int,
    ) -> None:
        self.tokenization_engine = tokenization_engine or TokenizationEngine()
        self.separators = separators
        self.min_tokens = min_tokens
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def split(self, text: str) -> list[str]:
        """Return budget-compliant chunks from one oversized text span."""
        stripped = text.strip()
        if not stripped:
            return []
        pieces = self._split_recursively(stripped, separators=self.separators)
        return self._merge_pieces(pieces)

    def _split_recursively(
        self,
        text: str,
        *,
        separators: tuple[str, ...],
    ) -> list[str]:
        """Recursively split text by increasingly fine-grained separators."""
        if self.tokenization_engine.count_tokens(text) <= self.max_tokens:
            return [text.strip()]
        if not separators:
            return self._token_window_fallback(text)
        parts = self._split_keep_separator(text=text, separator=separators[0])
        if len(parts) <= 1:
            return self._split_recursively(text, separators=separators[1:])
        return self._split_parts(parts=parts, separators=separators[1:])

    def _split_parts(
        self,
        *,
        parts: list[str],
        separators: tuple[str, ...],
    ) -> list[str]:
        """Split each part until every segment fits the max token budget."""
        segments: list[str] = []
        for part in parts:
            stripped = part.strip()
            if not stripped:
                continue
            segments.extend(self._split_recursively(stripped, separators=separators))
        return segments

    def _merge_pieces(self, pieces: list[str]) -> list[str]:
        """Merge undersized pieces back up to the target token budget."""
        merged: list[str] = []
        buffer: list[str] = []
        for piece in pieces:
            buffer = self._append_or_flush(piece=piece, buffer=buffer, merged=merged)
        self._flush_buffer(buffer=buffer, merged=merged)
        return merged

    def _append_or_flush(
        self,
        *,
        piece: str,
        buffer: list[str],
        merged: list[str],
    ) -> list[str]:
        """Append a piece when safe, otherwise flush the current buffer."""
        if not buffer:
            return [piece]
        candidate = self._join_parts([*buffer, piece])
        if self._should_merge(buffer=buffer, candidate=candidate):
            return [*buffer, piece]
        self._flush_buffer(buffer=buffer, merged=merged)
        return [piece]

    def _should_merge(self, *, buffer: list[str], candidate: str) -> bool:
        """Return whether the next piece should stay in the current chunk."""
        candidate_tokens = self.tokenization_engine.count_tokens(candidate)
        if candidate_tokens <= self.target_tokens:
            return True
        buffer_text = self._join_parts(buffer)
        buffer_tokens = self.tokenization_engine.count_tokens(buffer_text)
        return buffer_tokens < self.min_tokens and candidate_tokens <= self.max_tokens

    def _flush_buffer(self, *, buffer: list[str], merged: list[str]) -> None:
        """Flush the buffer into merged output if it has real content."""
        text = self._join_parts(buffer)
        if text:
            merged.append(text)

    def _token_window_fallback(self, text: str) -> list[str]:
        """Fallback to overlapping token windows when recursion bottoms out."""
        tokens = self.tokenization_engine.tokenize(text)
        windows = self.tokenization_engine.window_tokens(
            tokens=tokens,
            window_size=self.target_tokens,
            overlap=self.overlap_tokens,
        )
        return [self.tokenization_engine.detokenize(window) for window in windows]

    def _split_keep_separator(self, *, text: str, separator: str) -> list[str]:
        """Split text while keeping separators attached to prior segments."""
        raw_parts = text.split(separator)
        parts: list[str] = []
        for index, part in enumerate(raw_parts):
            suffix = separator if index < len(raw_parts) - 1 else ""
            combined = f"{part}{suffix}".strip()
            if combined:
                parts.append(combined)
        return parts

    def _join_parts(self, parts: list[str]) -> str:
        """Join buffered parts using paragraph-safe spacing."""
        return "\n\n".join(part.strip() for part in parts if part.strip()).strip()
