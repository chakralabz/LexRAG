"""Resolve paths and build parser-ready file load results."""

from __future__ import annotations

from pathlib import Path

from lexrag.ingestion.file_ingestion.file_path_resolver import FilePathResolver
from lexrag.ingestion.file_ingestion.inspection.file_inspection_service import (
    FileInspectionService,
)
from lexrag.ingestion.file_ingestion.loading.batch_file_collector import (
    BatchFileCollector,
)
from lexrag.ingestion.file_ingestion.loading.load_failure_reason_mapper import (
    LoadFailureReasonMapper,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_config import (
    FileIngestionConfig,
)
from lexrag.ingestion.file_ingestion.schemas.file_ingestion_report import (
    FileIngestionReport,
)
from lexrag.ingestion.file_ingestion.schemas.file_load_result import FileLoadResult


class FileLoadService:
    """Turn caller paths into structured parser-ready load decisions.

    Main entrypoint for file ingestion:
    resolve the path, inspect the file, and package the answer for the parser.
    """

    def __init__(
        self,
        config: FileIngestionConfig | None = None,
        *,
        inspection_service: FileInspectionService | None = None,
        resolver: FilePathResolver | None = None,
    ) -> None:
        """Wire together the loader collaborators.

        Args:
            config: Optional shared ingestion configuration.
            inspection_service: Optional inspection service override.
            resolver: Optional path resolver override.
        """
        self.config = config or FileIngestionConfig()
        self.inspection_service = inspection_service or FileInspectionService(
            config=self.config
        )
        self.resolver = resolver or FilePathResolver(config=self.config)
        self.batch_collector = BatchFileCollector(config=self.config)
        self.failure_reason_mapper = LoadFailureReasonMapper()

    def load_file(self, path: str | Path) -> FileLoadResult:
        """Load one file path into a parser-ready inspection result.

        Args:
            path: Caller-supplied file path.

        Returns:
            Structured load result for the resolved file.
        """
        requested = str(path)
        resolved = self.resolver.resolve(path)
        self._assert_file(resolved)
        report = self.inspection_service.inspect(resolved)
        return self._build_result(
            requested_path=requested,
            resolved_path=resolved,
            report=report,
        )

    def load_path(
        self,
        path: str | Path,
        *,
        recursive: bool = False,
    ) -> list[FileLoadResult]:
        """Expand a file or directory path into deterministic load results.

        Args:
            path: Caller-supplied file or directory path.
            recursive: Whether directory expansion should recurse into children.

        Returns:
            Structured load results in deterministic order.
        """
        requested = str(path)
        resolved = self.resolver.resolve(path)
        if resolved.is_file():
            return [self.load_file(resolved)]
        candidates = self.batch_collector.collect(path=resolved, recursive=recursive)
        return self._load_candidates(requested_path=requested, candidates=candidates)

    def _load_candidates(
        self,
        *,
        requested_path: str,
        candidates: list[Path],
    ) -> list[FileLoadResult]:
        """Resolve a candidate list and preserve the original input ordering.

        Args:
            requested_path: Original caller-provided path string.
            candidates: Concrete filesystem candidates to resolve and inspect.

        Returns:
            Load results aligned with the input candidate ordering.
        """
        resolved_specs, failed = self._resolve_candidates(
            requested_path=requested_path,
            candidates=candidates,
        )
        resolved_files = [path for _index, path in resolved_specs]
        if not resolved_files:
            return [failed[index] for index in sorted(failed)]
        reports = self.inspection_service.inspect_batch(resolved_files)
        loaded = self._build_batch_results(
            requested_path=requested_path,
            files=resolved_files,
            reports=reports,
        )
        loaded_by_index = {
            index: result
            for (index, _path), result in zip(resolved_specs, loaded, strict=True)
        }
        return [
            loaded_by_index.get(index) or failed[index]
            for index in range(len(candidates))
            if index in loaded_by_index or index in failed
        ]

    def _resolve_candidates(
        self,
        *,
        requested_path: str,
        candidates: list[Path],
    ) -> tuple[list[tuple[int, Path]], dict[int, FileLoadResult]]:
        """Resolve individual batch entries while preserving per-item failures.

        Args:
            requested_path: Original caller-provided path string.
            candidates: Concrete filesystem candidates to resolve.

        Returns:
            A pair of resolved file specifications and indexed failure results.
        """
        resolved_files: list[tuple[int, Path]] = []
        failed: dict[int, FileLoadResult] = {}
        for index, candidate in enumerate(candidates):
            try:
                resolved_files.append((index, self.resolver.resolve(candidate)))
            except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
                failed[index] = self._build_failed_result(
                    requested_path=requested_path,
                    candidate_path=candidate,
                    reason=self.failure_reason_mapper.map(exc),
                    message=str(exc),
                )
        return resolved_files, failed

    def _build_batch_results(
        self,
        *,
        requested_path: str,
        files: list[Path],
        reports: list[FileIngestionReport],
    ) -> list[FileLoadResult]:
        """Convert inspection reports into parser-ready batch results.

        Args:
            requested_path: Original caller-provided path string.
            files: Resolved file paths that were inspected successfully.
            reports: Inspection reports for the resolved files.

        Returns:
            Parser-ready load results for the inspected files.
        """
        return [
            self._build_result(
                requested_path=requested_path,
                resolved_path=path,
                report=report,
            )
            for path, report in zip(files, reports, strict=True)
        ]

    def _build_result(
        self,
        *,
        requested_path: str,
        resolved_path: Path,
        report: FileIngestionReport,
    ) -> FileLoadResult:
        """Package a successful inspection into the canonical result model.

        Args:
            requested_path: Original caller-provided path string.
            resolved_path: Canonical resolved path to the file.
            report: Inspection report for the resolved file.

        Returns:
            Successful parser-ready load result.
        """
        validation = report.validation
        return FileLoadResult(
            requested_path=requested_path,
            resolved_path=str(resolved_path),
            ingestion_report=report,
            is_ready=validation.is_valid,
            rejection_reason=validation.failure_reason,
        )

    def _build_failed_result(
        self,
        *,
        requested_path: str,
        candidate_path: Path,
        reason: str,
        message: str,
    ) -> FileLoadResult:
        """Package a pre-inspection failure into the canonical result model.

        Args:
            requested_path: Original caller-provided path string.
            candidate_path: Candidate path that failed before inspection.
            reason: Stable rejection reason code.
            message: Human-readable failure detail.

        Returns:
            Failed parser-ready load result.
        """
        return FileLoadResult(
            requested_path=requested_path,
            resolved_path=str(candidate_path),
            ingestion_report=None,
            is_ready=False,
            rejection_reason=reason,
            failure_message=message,
        )

    def _assert_file(self, path: Path) -> None:
        """Ensure the resolved single-path target is a file.

        Args:
            path: Resolved path to validate.
        """
        if path.is_file():
            return
        raise FileNotFoundError(f"Document is not a file: {path}")
