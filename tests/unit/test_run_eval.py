import json
import subprocess
from pathlib import Path


def test_eval_runner_cli_smoke() -> None:
    result = subprocess.run(
        ["python", "eval/run_eval.py", "--split", "ci"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Loaded" in result.stdout
    assert "Not implemented" in result.stdout

    qa_path = Path("eval/dataset/qa_pairs.json")
    qa_pairs = json.loads(qa_path.read_text(encoding="utf-8"))
    assert len(qa_pairs) == 10
