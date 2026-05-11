"""Reusable byte-sample heuristics for text-like payload detection."""

from __future__ import annotations


class TextSampleInspector:
    """Identify whether a leading byte sample behaves like UTF-8 text."""

    def is_likely_text(self, *, sample: bytes) -> bool:
        """Return whether the sample can safely be treated as text-like.

        Args:
            sample: Leading byte window from a file.

        Returns:
            True when the sample looks like UTF-8 text and not binary data.
        """
        if not sample or b"\x00" in sample:
            return False
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
