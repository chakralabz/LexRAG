"""Timing helpers for consistent latency instrumentation."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import ParamSpec, TypeVar

from lexrag.observability.logging_runtime import get_logger

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def log_duration(
    operation: str,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
    precision: int = 2,
) -> Generator[None]:
    """Logs elapsed execution time for a scoped operation.

    Args:
        operation: Human-readable operation name.
        logger: Logger used to emit the timing message.
        level: Logging level for the duration message.
        precision: Number of fractional digits for milliseconds.

    Yields:
        Control to the wrapped block.
    """
    active_logger = logger or get_logger()
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        active_logger.log(
            level,
            "%s completed in %.*f ms",
            operation,
            precision,
            elapsed_ms,
        )


def timed(
    operation: str | None = None,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorates a callable to log execution duration.

    Args:
        operation: Optional operation name. Defaults to function name.
        logger: Logger used to emit duration events.
        level: Logging level for duration events.

    Returns:
        Decorator that wraps a callable with timing instrumentation.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """Wraps a callable to emit duration metrics on each invocation."""
        op_name = operation or func.__name__

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """Runs the function while capturing elapsed time."""
            with log_duration(op_name, logger=logger, level=level):
                return func(*args, **kwargs)

        return wrapper

    return decorator
