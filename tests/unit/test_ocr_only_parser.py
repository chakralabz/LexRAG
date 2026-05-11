from __future__ import annotations

from pathlib import Path

import pytest

from lexrag.ingestion.parser.ocr_extractor import OCRExtractor
from lexrag.ingestion.parser.ocr_only_parser import OCROnlyParser
from lexrag.ingestion.parser.pdf_page_rasterizer import PdfPageRasterizer
from lexrag.ingestion.parser.schemas import OCRTextBlock, RasterizedPage


class StubOCRExtractor(OCRExtractor):
    def __init__(self, *, payload_by_page: dict[int, list[OCRTextBlock]]) -> None:
        self.payload_by_page = payload_by_page

    def extract(self, *, image_path: Path, page_number: int) -> list[OCRTextBlock]:
        _ = image_path
        return list(self.payload_by_page.get(page_number, []))


class StubPdfPageRasterizer(PdfPageRasterizer):
    def __init__(self, *, pages: list[RasterizedPage]) -> None:
        super().__init__(dpi=300)
        self.pages = pages

    def rasterize(self, *, path: Path, output_dir: Path) -> list[RasterizedPage]:
        _ = path, output_dir
        return list(self.pages)


def test_ocr_only_parser_parses_image_documents(tmp_path: Path) -> None:
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"fake-image")
    parser = OCROnlyParser(
        ocr_extractor=StubOCRExtractor(
            payload_by_page={
                1: [
                    OCRTextBlock(
                        page=1,
                        order=1,
                        text="Scanned contract heading",
                        confidence=0.91,
                    )
                ]
            }
        )
    )

    blocks = parser.parse(image_path)

    assert len(blocks) == 1
    assert blocks[0].text == "Scanned contract heading"
    assert blocks[0].is_ocr is True
    assert blocks[0].ocr_used == "stubocr"


def test_ocr_only_parser_rasterizes_pdf_pages_before_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    parser = OCROnlyParser(
        ocr_extractor=StubOCRExtractor(
            payload_by_page={
                1: [OCRTextBlock(page=1, order=1, text="First page", confidence=0.80)],
                2: [OCRTextBlock(page=2, order=1, text="Second page", confidence=0.75)],
            }
        ),
        pdf_rasterizer=StubPdfPageRasterizer(
            pages=[
                RasterizedPage(page_number=1, image_path=tmp_path / "p1.png"),
                RasterizedPage(page_number=2, image_path=tmp_path / "p2.png"),
            ]
        ),
    )

    blocks = parser.parse(pdf_path)

    assert [block.page for block in blocks] == [1, 2]
    assert [block.text for block in blocks] == ["First page", "Second page"]


def test_ocr_only_parser_rejects_empty_ocr_output(tmp_path: Path) -> None:
    image_path = tmp_path / "empty.png"
    image_path.write_bytes(b"fake-image")
    parser = OCROnlyParser(ocr_extractor=StubOCRExtractor(payload_by_page={1: []}))

    with pytest.raises(RuntimeError, match="no usable text"):
        parser.parse(image_path)
