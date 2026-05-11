"""Builds a grounded eval dataset from downloaded arXiv metadata."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from tqdm import tqdm

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexrag.utils.cli import add_optional_limit_args, resolve_optional_limit
from lexrag.utils.logging import get_logger
from lexrag.utils.text import TextNormalizer

logger = get_logger(__name__)
TEXT_NORMALIZER = TextNormalizer()


@dataclass(frozen=True, slots=True)
class DatasetBuildConfig:
    """Resolved limits used by dataset generation."""

    max_papers: int | None
    testcase_size: int | None


def parse_args() -> argparse.Namespace:
    """Parses CLI args for arXiv QA dataset generation."""
    parser = argparse.ArgumentParser(description="Build arXiv eval QA pairs")
    parser.add_argument(
        "--metadata-path",
        default="data/arxiv/raw/metadata/papers.jsonl",
        help="Path to arXiv metadata JSONL produced by download script",
    )
    parser.add_argument(
        "--output-path",
        default="data/arxiv/qa_pairs.json",
        help="Output path for generated QA dataset",
    )
    add_optional_limit_args(
        parser,
        arg_name="max-papers",
        default=50,
        help_text="Maximum papers to include in the generated dataset.",
        no_limit_help_text="Include all available metadata records.",
    )
    parser.add_argument(
        "--testcases-output-path",
        default="data/arxiv/testcases/qa_pairs_ci.json",
        help="Output path for lightweight CI testcase dataset",
    )
    add_optional_limit_args(
        parser,
        arg_name="testcases-size",
        default=25,
        help_text="Maximum records in the lightweight testcase dataset.",
        no_limit_help_text="Include all generated records in testcase output.",
    )
    return parser.parse_args()


def _truncate_words(text: str, limit: int) -> str:
    return TEXT_NORMALIZER.truncate_words(text, limit=limit)


def _doc_id_from_pdf_path(pdf_path: str) -> str:
    return TEXT_NORMALIZER.sanitize_identifier(Path(pdf_path).stem, default="doc")


def _load_records(path: Path, max_papers: int | None) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if max_papers is not None and len(records) >= max_papers:
                break
    return records


def _resolve_build_config(args: argparse.Namespace) -> DatasetBuildConfig:
    return DatasetBuildConfig(
        max_papers=resolve_optional_limit(
            args,
            limit_dest="max_papers",
            no_limit_dest="no_max_papers_limit",
        ),
        testcase_size=resolve_optional_limit(
            args,
            limit_dest="testcases_size",
            no_limit_dest="no_testcases_size_limit",
        ),
    )


def _validate_metadata_path(metadata_path: Path) -> None:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")


def _build_question_rows(
    *,
    index: int,
    title: str,
    lead_summary: str,
    first_author: str,
    doc_id: str,
    arxiv_id: str,
) -> list[dict[str, object]]:
    return [
        {
            "question_id": f"arxiv_fact_{index:03d}",
            "question": f"Which arXiv paper matches this abstract snippet: {lead_summary} ?",
            "gold_answer": title,
            "gold_chunk_ids": [],
            "gold_doc_ids": [doc_id],
            "difficulty": "factoid",
            "notes": f"arxiv_id={arxiv_id}",
        },
        {
            "question_id": f"arxiv_temp_{index:03d}",
            "question": f"Find the paper by {first_author} with title related to: {title}",
            "gold_answer": title,
            "gold_chunk_ids": [],
            "gold_doc_ids": [doc_id],
            "difficulty": "temporal",
            "notes": f"arxiv_id={arxiv_id}",
        },
    ]


def _build_qa_pairs(records: list[dict[str, object]]) -> list[dict[str, object]]:
    qa_pairs: list[dict[str, object]] = []
    for index, record in enumerate(
        tqdm(records, desc="Building QA pairs", unit="paper"), start=1
    ):
        title = str(record.get("title", "")).strip()
        summary = str(record.get("summary", "")).strip()
        authors = record.get("authors", [])
        pdf_path = str(record.get("pdf_path", "")).strip()
        if (
            not title
            or not summary
            or not isinstance(authors, list)
            or not authors
            or not pdf_path
        ):
            continue
        qa_pairs.extend(
            _build_question_rows(
                index=index,
                title=title,
                lead_summary=_truncate_words(summary, limit=28),
                first_author=str(authors[0]).strip(),
                doc_id=_doc_id_from_pdf_path(pdf_path),
                arxiv_id=str(record.get("arxiv_id", "")).strip(),
            )
        )
    return qa_pairs


def _write_dataset(path: Path, payload: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_outputs(
    *,
    qa_pairs: list[dict[str, object]],
    config: DatasetBuildConfig,
    output_path: Path,
    testcase_output_path: Path,
) -> list[dict[str, object]]:
    _write_dataset(output_path, qa_pairs)
    testcase_records = (
        qa_pairs if config.testcase_size is None else qa_pairs[: config.testcase_size]
    )
    _write_dataset(testcase_output_path, testcase_records)
    return testcase_records


def main() -> int:
    """Generates QA pairs linked to real arXiv documents."""
    args = parse_args()
    config = _resolve_build_config(args)
    metadata_path = Path(args.metadata_path)
    _validate_metadata_path(metadata_path)
    records = _load_records(metadata_path, config.max_papers)
    qa_pairs = _build_qa_pairs(records)
    output_path = Path(args.output_path)
    testcase_output_path = Path(args.testcases_output_path)
    testcase_records = _write_outputs(
        qa_pairs=qa_pairs,
        config=config,
        output_path=output_path,
        testcase_output_path=testcase_output_path,
    )
    logger.info(
        "Built arXiv QA datasets questions=%d output=%s testcase_output=%s testcase_questions=%d",
        len(qa_pairs),
        output_path,
        testcase_output_path,
        len(testcase_records),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
