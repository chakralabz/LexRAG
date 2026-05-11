.PHONY: format lint test eval ingest serve precommit

format:
	uv run --extra dev ruff format .

lint:
	uv run --extra dev ruff check . --fix
	uv run --extra dev python -m mypy lexrag

test:
	uv run --extra dev pytest tests/

eval:
	python scripts/03_run_eval.py --split ci

ingest:
	python ingestion/pipeline.py --input data/raw/ --limit 10

serve:
	python -m lexrag.serving.server --host 0.0.0.0 --port 8000

precommit:
	uv run --extra dev pre-commit run --all-files
