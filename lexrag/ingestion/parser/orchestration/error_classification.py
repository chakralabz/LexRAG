"""Helpers for stable parse failure classification."""

from __future__ import annotations


def classify_parse_error(error: Exception) -> str:
    """Map backend errors into stable, metrics-friendly reason codes."""
    message = str(error).lower()
    if isinstance(error, ModuleNotFoundError):
        return "primary_dependency_missing"
    if "not installed" in message or "no module named" in message:
        return "primary_dependency_missing"
    if "empty content" in message or "no extractable text" in message:
        return "primary_empty_output"
    if isinstance(error, TimeoutError):
        return "primary_timeout"
    if "manual recovery" in message or "encrypted" in message:
        return "manual_recovery_required"
    return "primary_parse_error"
