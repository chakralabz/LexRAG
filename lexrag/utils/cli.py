"""Shared CLI helpers for consistent script argument behavior."""

from __future__ import annotations

import argparse


def positive_int(value: str) -> int:
    """Parses a strictly positive integer argument value."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return parsed


def add_optional_limit_args(
    parser: argparse.ArgumentParser,
    *,
    arg_name: str,
    default: int,
    help_text: str,
    no_limit_help_text: str,
    no_limit_flag_name: str | None = None,
) -> tuple[str, str]:
    """Adds a standard `<limit>` + `<no-limit>` pair to a parser.

    Args:
        parser: Target argument parser.
        arg_name: Long option name without prefix (for example `max-results`).
        default: Default bounded limit.
        help_text: Help text for the bounded limit argument.
        no_limit_help_text: Help text for the boolean unlimited flag.
        no_limit_flag_name: Optional explicit flag name without leading `--`.

    Returns:
        Tuple of `(limit_dest, no_limit_dest)` argument destination names.
    """
    parser.add_argument(
        f"--{arg_name}",
        type=positive_int,
        default=default,
        help=help_text,
    )
    resolved_no_limit_flag_name = no_limit_flag_name or f"no-{arg_name}-limit"
    parser.add_argument(
        f"--{resolved_no_limit_flag_name}",
        action="store_true",
        help=no_limit_help_text,
    )
    return (
        arg_name.replace("-", "_"),
        resolved_no_limit_flag_name.replace("-", "_"),
    )


def resolve_optional_limit(
    args: argparse.Namespace, *, limit_dest: str, no_limit_dest: str
) -> int | None:
    """Resolves optional limit value from the standard parser pair."""
    return (
        None if bool(getattr(args, no_limit_dest)) else int(getattr(args, limit_dest))
    )
