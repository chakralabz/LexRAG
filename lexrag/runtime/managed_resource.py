"""Thread-safe lifecycle wrapper for heavyweight resources."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Generic, TypeVar

ResourceT = TypeVar("ResourceT")


class ManagedResource(Generic[ResourceT]):
    """Load, cache, and tear down one heavyweight runtime dependency."""

    def __init__(
        self,
        *,
        loader: Callable[[], ResourceT],
        finalizer: Callable[[ResourceT], None] | None = None,
    ) -> None:
        self._loader = loader
        self._finalizer = finalizer
        self._resource: ResourceT | None = None
        self._lock = RLock()

    @property
    def loaded(self) -> bool:
        """Return whether the wrapped resource has been initialized."""
        with self._lock:
            return self._resource is not None

    def load(self) -> ResourceT:
        """Initialize the resource once and return the cached instance."""
        with self._lock:
            if self._resource is None:
                self._resource = self._loader()
            return self._resource

    def get(self) -> ResourceT:
        """Return the cached resource, loading it on first access."""
        return self.load()

    def close(self) -> None:
        """Release the cached resource and run the configured finalizer."""
        with self._lock:
            if self._resource is None:
                return
            if self._finalizer is not None:
                self._finalizer(self._resource)
            self._resource = None
