"""Retry helpers for transient failures."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def _validate_retry_config(
    *,
    max_attempts: int,
    initial_delay: float,
    backoff: float,
    max_delay: float,
    jitter: float,
) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if initial_delay < 0:
        raise ValueError("initial_delay must be >= 0")
    if backoff < 1:
        raise ValueError("backoff must be >= 1")
    if max_delay <= 0:
        raise ValueError("max_delay must be > 0")
    if jitter < 0:
        raise ValueError("jitter must be >= 0")


def _compute_sleep_for(*, delay: float, max_delay: float, jitter: float) -> float:
    sleep_for = min(delay, max_delay)
    if jitter:
        sleep_for += random.uniform(0.0, jitter)
    return sleep_for


def _log_retry(
    *,
    logger: logging.Logger | None,
    func_name: str,
    sleep_for: float,
    next_attempt: int,
    max_attempts: int,
) -> None:
    if logger is None:
        return
    logger.warning(
        "Retrying %s in %.2fs (attempt %d/%d)",
        func_name,
        sleep_for,
        next_attempt,
        max_attempts,
    )


def retry(
    *,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    initial_delay: float = 0.2,
    backoff: float = 2.0,
    max_delay: float = 2.0,
    jitter: float = 0.0,
    sleep_fn: Callable[[float], None] = time.sleep,
    logger: logging.Logger | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retries a function call with exponential backoff."""
    _validate_retry_config(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff=backoff,
        max_delay=max_delay,
        jitter=jitter,
    )

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return _run_with_retry(
                func,
                args=args,
                kwargs=kwargs,
                exceptions=exceptions,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                backoff=backoff,
                max_delay=max_delay,
                jitter=jitter,
                sleep_fn=sleep_fn,
                logger=logger,
            )

        return wrapper

    return decorator


def _run_with_retry(
    func: Callable[..., R],
    *,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    exceptions: tuple[type[BaseException], ...],
    max_attempts: int,
    initial_delay: float,
    backoff: float,
    max_delay: float,
    jitter: float,
    sleep_fn: Callable[[float], None],
    logger: logging.Logger | None,
) -> R:
    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions:
            if attempt == max_attempts:
                raise
            sleep_for = _compute_sleep_for(
                delay=delay, max_delay=max_delay, jitter=jitter
            )
            _log_retry(
                logger=logger,
                func_name=func.__name__,
                sleep_for=sleep_for,
                next_attempt=attempt + 1,
                max_attempts=max_attempts,
            )
            sleep_fn(sleep_for)
            delay = min(delay * backoff, max_delay)
    raise RuntimeError("Retry wrapper ended unexpectedly.")
