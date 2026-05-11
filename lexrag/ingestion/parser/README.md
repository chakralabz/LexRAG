# `lexrag.ingestion.parser`

This package owns parsing layer responsibilities from
[docs/architecture.md](/Users/ayushsolanki/Desktop/Projects/LexRAG/docs/architecture.md):

1. Accept a caller path only after the file-ingestion boundary approves it
2. Choose the parser route deterministically from validated file metadata
3. Execute the fallback parser chain without silently dropping documents
4. Annotate every parsed block with parser provenance and confidence signals

## Responsibilities

- Consume outputs from `lexrag.ingestion.file_ingestion` rather than duplicating
  its path resolution, MIME checks, extension policy, antivirus hooks, or
  encrypted/corrupt file rejection logic
- Route files into `docling`, `pymupdf`, `unstructured`, OCR-only, or manual
  recovery based on file family and lightweight PDF heuristics
- Emit canonical `ParsedBlock` and `DocumentParseResult` models for downstream
  normalization and chunking
- Preserve auditability through `ParseAttempt`, fallback metadata, and
  parse-confidence annotation

## Terminology

The package now uses one terminology model throughout:

- `DocumentParser`: parses one approved document
- `DocumentParseResult`: the actual parse payload for that document
- `LoadedDocumentParserPipeline`: stage adapter that accepts a
  `FileLoadResult` and returns a terminal parser-stage result
- `LoadedDocumentParseResult`: outer wrapper that combines loader context,
  parser status, and an optional `DocumentParseResult`

## Package structure

- `orchestration/`: routing, fallback execution, and public parser entrypoints
- `backends/`: backend adapters such as Docling and OCR-only parsing
- `docling/`: Docling converter factory, warmup, and result normalization
- `ocr/`: OCR extraction, runtime validation, and PDF rasterization
- `builders/`: shared canonical block construction helpers
- `schemas/`: parser-only config and parser DTOs
- top-level modules: compatibility shims for older imports

## Main objects

- `DocumentParser`: main orchestration entrypoint for one file
- `LoadedDocumentParserPipeline`: transition adapter from `FileLoadResult`
  into parser execution
- `LoadedDocumentParseResult`: terminal parser-stage wrapper result
- `DoclingParser.preload()`: eager warmup hook for model-heavy Docling startup
- `OCROnlyParser.preload()`: startup validation for Tesseract-backed OCR
- `ParserSelectionStrategy`: deterministic route planner
- `ParserChainExecutor`: backend execution with structured attempts
- `ParserProvenanceAnnotator`: parser metadata and confidence attachment

## Expected flow

```text
caller path
  -> FileLoadService
  -> FileLoadResult
  -> LoadedDocumentParserPipeline | DocumentParser.parse_loaded_file(...)
  -> ParserSelectionStrategy
  -> ParserChainExecutor
      -> docling | pymupdf | unstructured | ocr_only | manual_recovery
  -> ParserProvenanceAnnotator
  -> LoadedDocumentParseResult / DocumentParseResult
```

## Usage

```python
from pathlib import Path

from lexrag.ingestion.file_ingestion import FileIngestionConfig, FileLoadService
from lexrag.ingestion.parser import (
    DocumentParser,
    LoadedDocumentParserPipeline,
    ParserConfig,
)

loader_config = FileIngestionConfig.from_options(
    allowed_root_paths=("/data/contracts",),
    max_file_size_mb=25,
)
parser_config = ParserConfig.from_options(ocr_render_dpi=400)
loader = FileLoadService(config=loader_config)
parser_pipeline = LoadedDocumentParserPipeline(
    parser=DocumentParser(config=parser_config, file_loader=loader)
)
load_result = loader.load_file(Path("/data/contracts/master-service-agreement.pdf"))
loaded_document_result = parser_pipeline.parse_loaded_file(load_result)

if loaded_document_result.status == "parsed":
    print(loaded_document_result.document_parse_result.parser_used)
else:
    print(
        loaded_document_result.file_load_result.rejection_reason
        or loaded_document_result.error_message
    )
```

To pay Docling and OCR initialization cost during service startup instead of on
the first user request:

```python
parser = DocumentParser(config=parser_config, file_loader=loader)
parser.preload()
```

When you want offline or deterministic startup, pre-download Docling artifacts
and point `parser_config.docling.artifacts_path` at that directory.
If you want startup to fail when the path is missing, set
`parser_config.docling.require_local_artifacts=True`.
If you want warmup to prefetch Docling artifacts, set
`parser_config.docling.preload_artifacts=True`.
For standalone OCR startup validation, set `parser_config.ocr.preload_backend=True`.

For directory-style parsing:

```python
load_results = loader.load_path("/data/uploads", recursive=True)
results = parser_pipeline.parse_loaded_files(load_results)
parsed = [item for item in results if item.status == "parsed"]
rejected = [item for item in results if item.status == "rejected"]
quarantined = [item for item in results if item.status == "quarantined"]
```
