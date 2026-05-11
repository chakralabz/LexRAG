"""Small in-memory rate limiter for the ASGI serving surface."""

from __future__ import annotations

from threading import Lock
from time import monotonic


class FixedWindowRateLimiter:
    """Apply a per-key fixed-window request budget."""

    def __init__(self, *, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = Lock()
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, *, key: str) -> bool:
        with self._lock:
            return self._allow_locked(key=key)

    def _allow_locked(self, *, key: str) -> bool:
        now = monotonic()
        reset_at, count = self._windows.get(key, (0.0, 0))
        if now >= reset_at:
            self._windows[key] = (now + self.window_seconds, 1)
            return True
        if count >= self.limit:
            return False
        self._windows[key] = (reset_at, count + 1)
        return True
