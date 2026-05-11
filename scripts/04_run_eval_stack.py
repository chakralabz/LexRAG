"""Production-like retrieval-eval CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexrag.eval.cli import run_stack_cli


def main() -> int:
    """Runs retrieval eval against external stores (Qdrant/Elasticsearch)."""
    return run_stack_cli()


if __name__ == "__main__":
    raise SystemExit(main())
