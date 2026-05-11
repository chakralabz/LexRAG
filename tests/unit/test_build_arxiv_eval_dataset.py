import json
import subprocess
from pathlib import Path


def _make_record(tmp_path: Path, index: int) -> dict[str, object]:
    return {
        "arxiv_id": f"2501.{index:05d}v1",
        "title": f"Paper {index}",
        "summary": f"Summary text for paper {index}.",
        "authors": [f"Author {index}"],
        "pdf_path": str(tmp_path / f"2501.{index:05d}v1.pdf"),
    }


def test_build_arxiv_eval_dataset_script(tmp_path: Path) -> None:
    metadata_path = tmp_path / "papers.jsonl"
    metadata_path.write_text(
        "\n".join(json.dumps(_make_record(tmp_path, index)) for index in range(1, 9)),
        encoding="utf-8",
    )
    output_path = tmp_path / "qa_pairs_arxiv.json"
    testcase_output_path = tmp_path / "qa_pairs_ci.json"

    result = subprocess.run(
        [
            "python",
            "scripts/02_build_arxiv_eval_dataset.py",
            "--metadata-path",
            str(metadata_path),
            "--output-path",
            str(output_path),
            "--testcases-output-path",
            str(testcase_output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()
    assert testcase_output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload) == 16
    assert all("gold_doc_ids" in item for item in payload)
    assert all("Synthetic" not in str(item.get("notes", "")) for item in payload)

    testcase_payload = json.loads(testcase_output_path.read_text(encoding="utf-8"))
    assert len(testcase_payload) == 16


def test_build_arxiv_eval_dataset_script_no_limit_flags_include_all_records(
    tmp_path: Path,
) -> None:
    metadata_path = tmp_path / "papers_full.jsonl"
    metadata_path.write_text(
        "\n".join(json.dumps(_make_record(tmp_path, index)) for index in range(1, 7)),
        encoding="utf-8",
    )
    output_path = tmp_path / "qa_pairs_arxiv_full.json"
    testcase_output_path = tmp_path / "qa_pairs_ci_full.json"

    result = subprocess.run(
        [
            "python",
            "scripts/02_build_arxiv_eval_dataset.py",
            "--metadata-path",
            str(metadata_path),
            "--output-path",
            str(output_path),
            "--testcases-output-path",
            str(testcase_output_path),
            "--no-max-papers-limit",
            "--no-testcases-size-limit",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    testcase_payload = json.loads(testcase_output_path.read_text(encoding="utf-8"))
    assert len(payload) == 12
    assert len(testcase_payload) == 12
