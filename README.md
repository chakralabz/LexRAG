# LexRAG

LexRAG is a reusable Python package for enterprise RAG ingestion and retrieval
pipelines. The repository now treats `lexrag/` as the product: application code
can depend on it, preload heavyweight resources at startup, and compose the
services it needs without importing a project-specific FastAPI app.

## Public SDK

```python
from lexrag import (
    EmbeddingService,
    ParserService,
    RAGPipeline,
)

parser_service = ParserService().load()
embedding_service = EmbeddingService().load()

pipeline = RAGPipeline(
    parser_service=parser_service,
    embedding_service=embedding_service,
)
chunks = pipeline.ingest(["/data/contracts/master-services-agreement.pdf"])
```

Top-level imports are intentionally stable:

```python
from lexrag import ConfigLoader, LexRAGSettings
from lexrag import FileValidationService, ChunkingService
from lexrag import AuditService, ObservabilityService
```

## FastAPI Startup Pattern

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lexrag import EmbeddingService, ParserService, RAGPipeline

parser_service = ParserService()
embedding_service = EmbeddingService()
pipeline = RAGPipeline(
    parser_service=parser_service,
    embedding_service=embedding_service,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    pipeline.load()
    try:
        yield
    finally:
        pipeline.close()


app = FastAPI(lifespan=lifespan)
```

This gives developers both modes:

- Eager startup loading for web services
- Lazy runtime loading for scripts, workers, and notebooks

## Package Design

- `lexrag.services`: stable service layer for validation, parsing,
  normalization, chunking, embedding, vector preparation, auditing, and
  observability
- `lexrag.pipeline`: reusable composition layer for ingestion and retrieval
- `lexrag.runtime`: thread-safe lifecycle wrappers for heavyweight resources
- `lexrag.config`: validated package settings plus YAML/ENV/override loading
- `lexrag.ingestion`, `lexrag.indexing`, `lexrag.retrieval`, `lexrag.generation`:
  lower-level building blocks and subsystem internals

## Configuration

```python
from lexrag import ConfigLoader

settings = ConfigLoader().load(
    config_path="config.yaml",
    overrides={"embed_batch_size": 16},
)
```

Source precedence is:

1. `config.yaml`
2. Environment variables
3. Explicit runtime overrides

## Developer Notes

- Keep application wiring outside the package when building APIs.
- Reuse `ParserService` and `EmbeddingService` instances across requests.
- Prefer dependency injection over importing deep internals from `lexrag.*`.
- Use [docs/architecture.md](/Users/ayushsolanki/Desktop/Projects/lexrag/docs/architecture.md)
  for subsystem behavior and [docs/package_sdk.md](/Users/ayushsolanki/Desktop/Projects/lexrag/docs/package_sdk.md)
  for SDK integration patterns.

## Hardening Status

Recent production-hardening work has focused on closing the gap between the
package architecture and runtime guarantees:

- The package now has a real serving entrypoint via `main.py` and
  `lexrag.serving.server`.
- Ingestion requires a strict `DocumentParserProtocol`; duck-typed parser
  bypasses are rejected.
- Production config fails closed when `API_SECRET_KEY` is missing.
- Dense and sparse indexing now use document-level coordinated writes with
  compensating rollback so partial sparse failures do not leave mixed-version
  indexes behind.
- The dedicated OCR route now supports scanned PDFs and image documents through
  rasterization plus Tesseract-backed extraction instead of failing as a
  placeholder path.
- Ingest requests now persist job records with durable status, summaries, and
  quarantine-visible per-document outcomes so operators can inspect manual
  recovery cases after the request returns.
- Idempotent ingest submission and targeted replay of failed or quarantined
  documents are now supported on top of the persisted ingest job model.

LexRAG is still under active hardening. Treat the repository as a serious
package foundation with improving operational guarantees, not as a finished
end-to-end hosted product.

## Project Context

LexRAG is a legal-domain retrieval-augmented generation system built in phases
with strict evaluation gates.

## Quick Start

1. Start local services:

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up -d
```

2. Install deps and git hooks:

```bash
uv sync --extra dev
uv run --extra dev pre-commit install
```

3. Run checks:

```bash
make lint
make test
make precommit
```

4. Run eval skeleton:

```bash
python eval/run_eval.py --split ci
```
