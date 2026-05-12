"""Tests for OCR helpers and the image / scanned-PDF parsers.

Fixtures used (created by tests/conftest_ocr.py at session start):
    - tests/fixtures/scanned_article.png — 1240×1754 rasterized text
    - tests/fixtures/scanned_article.pdf — same content, no text layer

We assert recall on a small set of keywords rather than exact F1 because:
    - tesseract's OCR may swap 'œ' ↔ '|' depending on antialiasing
    - the test runs on whatever Tesseract version the host happens to have
    - keyword recall is what the user actually cares about ("did the page
      come through as searchable text?")
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.parsers import parse_bytes
from app.parsers._ocr import is_tesseract_available, ocr_bytes

FIXTURES = Path(__file__).parent / "fixtures"


pytestmark = pytest.mark.skipif(
    not is_tesseract_available() or shutil.which("tesseract") is None,
    reason="Tesseract not installed on this host",
)


# These words appear in scanned_article.png with very high frequency and clear
# typography. If recall on these < 5/6 we have a real OCR regression.
KEYWORDS = ["lecture", "bionique", "typographique", "Casutt", "saccadique", "Snell"]
RECALL_TARGET = 5 / 6  # 5 out of 6 keywords must be recognized


def _normalise(text: str) -> str:
    return text.lower().replace("œ", "oe").replace("’", "'").replace("|", "l")


def test_image_parser_returns_text() -> None:
    data = (FIXTURES / "scanned_article.png").read_bytes()
    doc = parse_bytes("scanned_article.png", data)
    text = " ".join(b.text for b in doc.blocks if b.type != "spacer")
    assert text.strip()
    normalised = _normalise(text)
    hits = sum(_normalise(k) in normalised for k in KEYWORDS)
    assert hits / len(KEYWORDS) >= RECALL_TARGET, (
        f"OCR recall {hits}/{len(KEYWORDS)} below target {RECALL_TARGET:.0%}: text={text!r}"
    )


def test_image_parser_reports_confidence() -> None:
    data = (FIXTURES / "scanned_article.png").read_bytes()
    doc = parse_bytes("scanned_article.png", data)
    # The image parser appends a confidence warning.
    assert any("confiance" in w.lower() for w in doc.warnings)


def test_scanned_pdf_parser_returns_text() -> None:
    data = (FIXTURES / "scanned_article.pdf").read_bytes()
    doc = parse_bytes("scanned_article.pdf", data)
    text = " ".join(b.text for b in doc.blocks if b.type != "spacer")
    assert text.strip(), f"Scanned PDF returned empty text. Warnings: {doc.warnings}"
    normalised = _normalise(text)
    hits = sum(_normalise(k) in normalised for k in KEYWORDS)
    assert hits / len(KEYWORDS) >= RECALL_TARGET, (
        f"OCR recall {hits}/{len(KEYWORDS)} below target {RECALL_TARGET:.0%}: text={text!r}"
    )


def test_scanned_pdf_warns_about_ocr() -> None:
    data = (FIXTURES / "scanned_article.pdf").read_bytes()
    doc = parse_bytes("scanned_article.pdf", data)
    assert any("OCR" in w for w in doc.warnings)


def test_ocr_bytes_high_confidence() -> None:
    data = (FIXTURES / "scanned_article.png").read_bytes()
    result = ocr_bytes(data)
    assert result.mean_confidence >= 80.0, (
        f"OCR mean confidence too low: {result.mean_confidence}"
    )
    assert len(result.words) > 30
