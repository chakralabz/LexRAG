"""Persistence writer for eval result payloads."""

from __future__ import annotations

import json
from pathlib import Path


class EvalResultWriter:
    """Persists eval results to disk."""

    def write(
        self, *, results: dict[str, object], output_dir: Path, output_file: str
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_file
        output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return output_path
