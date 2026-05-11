"""Typed environment variable readers with strict validation."""

from __future__ import annotations

import os
from typing import Final

from lexrag.utils.configuration_error import ConfigurationError

_TRUE_VALUES: Final = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES: Final = {"0", "false", "f", "no", "n", "off"}


def _raise_missing(name: str) -> None:
    """Raises a standardized missing-environment error.

    Args:
        name: Environment variable name.

    Raises:
        ConfigurationError: Always raised to indicate missing configuration.
    """
    raise ConfigurationError(
        f"Environment variable {name!r} is required but was not provided."
    )


def get_env_str(
    name: str,
    default: str | None = None,
    *,
    required: bool = False,
    strip: bool = True,
) -> str:
    """Reads a string environment variable with optional normalization.

    Args:
        name: Environment variable name.
        default: Fallback value used when the variable is not set.
        required: Whether the variable must be present and non-empty.
        strip: Whether to strip leading and trailing whitespace.

    Returns:
        Resolved string value.

    Raises:
        ConfigurationError: If a required value is missing.
    """
    raw = os.getenv(name)

    if raw is None:
        if required and default is None:
            _raise_missing(name)
        if default is None:
            _raise_missing(name)
        assert default is not None
        return default

    value = raw.strip() if strip else raw
    if required and value == "":
        _raise_missing(name)
    return value


def get_env_bool(
    name: str, default: bool | None = None, *, required: bool = False
) -> bool:
    """Reads a boolean environment variable.

    Args:
        name: Environment variable name.
        default: Fallback value used when the variable is not set.
        required: Whether the variable must be present.

    Returns:
        Parsed boolean value.

    Raises:
        ConfigurationError: If a required value is missing or cannot be parsed.
    """
    raw = os.getenv(name)

    if raw is None:
        if required and default is None:
            _raise_missing(name)
        if default is None:
            _raise_missing(name)
        assert default is not None
        return default

    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False

    raise ConfigurationError(
        f"Environment variable {name!r} must be a boolean value, got {raw!r}."
    )


def _validate_range(
    name: str,
    value: int | float,
    *,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
) -> None:
    """Validates inclusive numeric bounds for a parsed environment value.

    Args:
        name: Environment variable name.
        value: Parsed numeric value.
        min_value: Optional inclusive lower bound.
        max_value: Optional inclusive upper bound.

    Raises:
        ConfigurationError: If the value is outside the configured range.
    """
    if min_value is not None and value < min_value:
        raise ConfigurationError(
            f"Environment variable {name!r} must be >= {min_value}, got {value}."
        )
    if max_value is not None and value > max_value:
        raise ConfigurationError(
            f"Environment variable {name!r} must be <= {max_value}, got {value}."
        )


def get_env_int(
    name: str,
    default: int | None = None,
    *,
    required: bool = False,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Reads an integer environment variable with optional range checks."""
    raw = os.getenv(name)
    if raw is None:
        if required and default is None:
            _raise_missing(name)
        if default is None:
            _raise_missing(name)
        assert default is not None
        value = default
    else:
        try:
            # ``strip`` tolerates accidental whitespace in deployed env files.
            value = int(raw.strip())
        except ValueError as exc:
            raise ConfigurationError(
                f"Environment variable {name!r} must be an integer, got {raw!r}."
            ) from exc

    _validate_range(name, value, min_value=min_value, max_value=max_value)
    return value


def get_env_float(
    name: str,
    default: float | None = None,
    *,
    required: bool = False,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    """Reads a float environment variable with optional range checks."""
    raw = os.getenv(name)
    if raw is None:
        if required and default is None:
            _raise_missing(name)
        if default is None:
            _raise_missing(name)
        assert default is not None
        value = default
    else:
        try:
            value = float(raw.strip())
        except ValueError as exc:
            raise ConfigurationError(
                f"Environment variable {name!r} must be a float, got {raw!r}."
            ) from exc

    _validate_range(name, value, min_value=min_value, max_value=max_value)
    return value
