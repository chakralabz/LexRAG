# LexRAG SDK Guide

## Overview

`lexrag` is designed as an internal platform package, not a single deployed
service. The package gives application teams a stable service layer for file
validation, parsing, normalization, chunking, embedding preparation, embedding,
vector serialization, auditing, and observability.

## Public API

Import package services directly from `lexrag`:

```python
from lexrag import (
    AuditService,
    ChunkingService,
    ConfigLoader,
    EmbeddingService,
    FileValidationService,
    ObservabilityService,
    ParserService,
    RAGPipeline,
    VectorPreparationService,
)
```

Avoid deep imports from internal folders in application code unless you are
extending package internals.

## Service Lifecycle

Heavy runtimes use explicit lifecycle management:

```python
from lexrag import EmbeddingService, ParserService

parser_service = ParserService()
embedding_service = EmbeddingService()

parser_service.load()
embedding_service.load()

# Reuse in many requests or jobs.

embedding_service.close()
parser_service.close()
```

This supports:

- FastAPI startup-time loading
- Lazy first-use initialization
- Safe reuse within long-lived worker processes

## Configuration Loading

```python
from lexrag import ConfigLoader

settings = ConfigLoader().load(
    config_path="config.yaml",
    overrides={"environment": "PROD"},
)
```

Configuration precedence:

1. YAML file
2. Environment variables
3. Explicit overrides

## Pipeline Composition

```python
from lexrag import (
    EmbeddingService,
    ParserService,
    RAGPipeline,
)

pipeline = RAGPipeline(
    parser_service=ParserService(),
    embedding_service=EmbeddingService(),
)

pipeline.load()
chunks = pipeline.ingest(["/data/corpus/policy.pdf"])
pipeline.close()
```

Applications can inject their own retrieval, store, metrics, or tracing
implementations without changing the package internals.

## FastAPI Integration

Use the package as a dependency, not as the whole app:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from lexrag import EmbeddingService, ParserService, RAGPipeline

pipeline = RAGPipeline(
    parser_service=ParserService(),
    embedding_service=EmbeddingService(),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    pipeline.load()
    try:
        yield
    finally:
        pipeline.close()
```

## Operational Guidance

- Instantiate heavy services once per process.
- Pass services into route handlers via your app container or dependency layer.
- Keep observability hooks at the application boundary.
- Treat `lexrag.serving` as optional example integration, not the package core.
