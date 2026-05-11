"""Build Docling PDF pipeline options from parser configuration.

The factory translates LexRAG's stable parser config into the subset of Docling
options available in the installed version. Unsupported fields are skipped
instead of raising, which keeps upgrades and partial feature sets manageable.
"""

from __future__ import annotations

from typing import Any

from lexrag.ingestion.parser.schemas.docling_config import DoclingConfig


class DoclingPipelineOptionsFactory:
    """Translate parser config into Docling pipeline option objects."""

    def __init__(self, *, config: DoclingConfig) -> None:
        self.config = config

    def build(self) -> Any:
        """Build the configured Docling PDF pipeline options."""
        try:
            from docling.datamodel.pipeline_options import PdfPipelineOptions
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Docling PDF pipeline options are unavailable.") from exc
        options = PdfPipelineOptions()
        # Options are applied in layers so feature-specific helpers remain small
        # and tests can exercise them independently.
        self._apply_common_pipeline_options(options=options)
        self._apply_table_options(options=options)
        self._apply_ocr_options(options=options)
        return options

    def _apply_common_pipeline_options(self, *, options: Any) -> None:
        """Apply top-level PDF pipeline settings shared across most documents."""
        config = self.config
        options.do_ocr = config.do_ocr
        options.do_table_structure = config.do_table_structure
        options.do_code_enrichment = config.do_code_enrichment
        options.do_formula_enrichment = config.do_formula_enrichment
        options.force_backend_text = config.force_backend_text
        options.generate_page_images = config.generate_page_images
        options.generate_parsed_pages = config.generate_parsed_pages
        options.generate_table_images = config.generate_table_images
        self._set_if_present(options, "artifacts_path", config.artifacts_path)
        self._set_if_present(
            options,
            "document_timeout",
            config.document_timeout_seconds,
        )
        self._set_if_present(
            options,
            "enable_remote_services",
            config.enable_remote_services,
        )
        self._set_if_present(
            options,
            "allow_external_plugins",
            config.allow_external_plugins,
        )
        self._set_if_present(options, "images_scale", config.images_scale)
        self._set_if_present(options, "ocr_batch_size", config.ocr_batch_size)
        self._set_if_present(options, "layout_batch_size", config.layout_batch_size)
        self._set_if_present(options, "table_batch_size", config.table_batch_size)
        self._set_if_present(
            options,
            "batch_polling_interval_seconds",
            config.batch_polling_interval_seconds,
        )
        self._set_if_present(options, "queue_max_size", config.queue_max_size)
        self._apply_accelerator_options(options=options)

    def _apply_table_options(self, *, options: Any) -> None:
        """Apply table extraction options when the runtime exposes them."""
        table_options = getattr(options, "table_structure_options", None)
        if table_options is None:
            return
        self._set_if_present(
            table_options,
            "do_cell_matching",
            self.config.table_cell_matching,
        )
        self._apply_table_mode(table_options=table_options)

    def _apply_table_mode(self, *, table_options: Any) -> None:
        """Apply TableFormer mode only when the enum exists in this Docling version."""
        mode_value = self.config.table_mode
        if mode_value is None:
            return
        try:
            from docling.datamodel.pipeline_options import TableFormerMode
        except Exception:  # pragma: no cover
            return
        enum_name = mode_value.value.upper()
        if hasattr(TableFormerMode, enum_name):
            self._set_if_present(table_options, "mode", getattr(TableFormerMode, enum_name))

    def _apply_accelerator_options(self, *, options: Any) -> None:
        """Apply accelerator settings when the runtime exposes them."""
        accelerator = getattr(options, "accelerator_options", None)
        if accelerator is None:
            return
        config = self.config.accelerator
        self._set_if_present(accelerator, "device", config.device.value)
        self._set_if_present(accelerator, "num_threads", config.num_threads)

    def _apply_ocr_options(self, *, options: Any) -> None:
        """Apply OCR configuration only when OCR is enabled in parser config."""
        if not self.config.do_ocr:
            return
        ocr_options = self._build_ocr_options()
        if ocr_options is not None:
            self._set_if_present(options, "ocr_options", ocr_options)

    def _build_ocr_options(self) -> Any | None:
        """Build the engine-specific Docling OCR options object."""
        config = self.config.ocr
        ocr_class = self._resolve_ocr_options_class(engine=config.engine.value)
        if ocr_class is None:
            return None
        options = ocr_class()
        # Different engines expose different knobs, so every assignment is
        # guarded by `_set_if_present`.
        self._set_if_present(options, "lang", list(config.languages) or None)
        self._set_if_present(
            options,
            "force_full_page_ocr",
            config.force_full_page_ocr,
        )
        self._set_if_present(
            options,
            "bitmap_area_threshold",
            config.bitmap_area_threshold,
        )
        self._set_if_present(
            options,
            "confidence_threshold",
            config.confidence_threshold,
        )
        self._set_if_present(
            options,
            "model_storage_directory",
            config.model_storage_directory,
        )
        self._set_if_present(options, "download_enabled", config.download_enabled)
        self._set_if_present(options, "use_gpu", config.use_gpu)
        self._set_if_present(options, "path", config.tesseract_data_path)
        self._set_if_present(
            options,
            "psm",
            config.tesseract_page_segmentation_mode,
        )
        return options

    def _resolve_ocr_options_class(self, *, engine: str) -> Any | None:
        """Resolve the Docling OCR options class for one engine id."""
        try:
            from docling.datamodel import pipeline_options as options_module
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Docling OCR options are unavailable.") from exc
        class_name = self._ocr_option_class_name(engine=engine)
        return getattr(options_module, class_name, None)

    def _ocr_option_class_name(self, *, engine: str) -> str:
        """Map stable engine ids to Docling option class names."""
        class_names = {
            "auto": "OcrAutoOptions",
            "easyocr": "EasyOcrOptions",
            "tesseract": "TesseractOcrOptions",
            "tesseract_cli": "TesseractCliOcrOptions",
            "ocrmac": "OcrMacOptions",
            "rapidocr": "RapidOcrOptions",
        }
        return class_names[engine]

    def _set_if_present(self, target: Any, field_name: str, value: Any) -> None:
        """Assign a field only when both the value and target attribute exist."""
        if value is None or not hasattr(target, field_name):
            return
        setattr(target, field_name, value)
