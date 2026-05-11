# `lexrag.ingestion.file_ingestion`

This package owns the pre-parse ingestion boundary described in
[docs/architecture.md](/Users/ayushsolanki/Desktop/Projects/LexRAG/docs/architecture.md).
It decides whether a filesystem path is safe to ingest and returns the
canonical file report the parser layer should trust.

## Responsibilities

1. Resolve caller-provided paths into canonical absolute paths
2. Enforce path safety rules such as root restrictions and symlink policy
3. Validate file integrity, extension policy, and upload safety
4. Detect file type from bytes instead of trusting extensions alone
5. Run malware scanning through an optional ClamAV integration
6. Return a stable, auditable load decision for downstream parser routing

## Main objects

- `FileLoadService`: the main entrypoint for callers that start with a path
- `FileInspectionService`: validation + type detection for already-resolved files
- `FilePathResolver`: canonical path resolution and path-boundary checks
- `FileValidationService`: size, extension, corruption, encryption, antivirus,
  and batch-duplicate checks
- `ClamAVAntivirusScanner`: optional open-source malware scanning via ClamAV
- `FileTypeDetector`: byte-level classification into parser-facing families

## Internal structure

- `antivirus/`: scanner interface, ClamAV integration, and scanner factory
- `classification/`: shared extension policy, document family routing, and
  text-sample heuristics
- `inspection/`: orchestrates validation and type detection
- `validation/`: lightweight integrity inspection and structured issue creation
- `loading/`: deterministic directory expansion and stable load failure mapping

The top-level modules remain the public API so downstream packages do not need
to know about the internal organization.

## Expected flow

```text
caller path
  -> FileLoadService
      -> FilePathResolver
      -> FileInspectionService
          -> FileValidationService
              -> antivirus/*
          -> FileTypeDetector
  -> FileLoadResult
  -> parser selection
```

## Usage

```python
from pathlib import Path

from lexrag.ingestion.file_ingestion import (
    FileIngestionAntivirusConfig,
    FileIngestionConfig,
    FileLoadService,
    SupportedFileType,
)

config = FileIngestionConfig.from_options(
    allowed_file_types=(SupportedFileType.PDF, SupportedFileType.DOCX),
    max_file_size_mb=25,
    max_page_count=200,
    antivirus=FileIngestionAntivirusConfig.clamav(
        socket_path="/var/run/clamd.sock"
    ),
)
loader = FileLoadService(config=config)
result = loader.load_file(Path("/data/contracts/master-service-agreement.pdf"))

if result.is_ready:
    print(result.ingestion_report.detection.document_family)
else:
    print(result.rejection_reason)
```

For directory-style ingestion:

```python
results = loader.load_path("/data/uploads", recursive=True)
ready = [item for item in results if item.is_ready]
rejected = [item for item in results if not item.is_ready]
```
