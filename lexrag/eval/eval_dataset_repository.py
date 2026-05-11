"""Dataset loading repository for eval QA pairs."""

from __future__ import annotations

import json
from pathlib import Path

from lexrag.indexing.schemas import QAPair


class EvalDatasetRepository:
    """Loads and validates eval QA pairs from JSON payloads."""

    def load(self, dataset_path: Path) -> list[QAPair]:
        raw_records = json.loads(dataset_path.read_text(encoding="utf-8"))
        return [QAPair.model_validate(record) for record in raw_records]
