"""PDF parser using PyMuPDF, with automatic OCR fallback for scanned PDFs.

Strategy
========
1. Extract the embedded text layer with `page.get_text("dict")`. This gives
   us font sizes per span — we use the dominant size as the "body" font and
   anything ≥ 1.25× as a heading.
2. If the embedded text layer is empty (or so sparse it cannot be the real
   content), we **OCR each page in turn** via `_ocr.py`. The page is
   rendered at `DPI` and Tesseract gives us word boxes + confidences.

Why per-page detection rather than a global `is_scanned` flag?
--------------------------------------------------------------
Real-world PDFs are often hybrid: a scanned cover page, a few text pages,
then a series of scanned figures. A per-page decision keeps the searchable
text we already have **and** OCRs the rest, instead of all-or-nothing.
"""
from __future__ import annotations

import logging

import fitz  # PyMuPDF

from ..models import Block
from . import _ocr

logger = logging.getLogger(__name__)


# A page is treated as "scanned" if its native text layer contains fewer
# alpha characters than this. We accept stray page numbers / watermarks
# without erroneously skipping OCR.
NATIVE_TEXT_MIN_ALPHA_CHARS = 40


def parse(data: bytes) -> tuple[list[Block], list[str]]:
    warnings: list[str] = []
    blocks: list[Block] = []

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        warnings.append(f"Failed to open PDF: {exc}")
        return blocks, warnings

    # Pre-compute the body font size on the full corpus of native spans so
    # heading detection is calibrated even when some pages OCR.
    sizes: list[float] = []
    for page in doc:
        page_dict = page.get_text("dict")
        for blk in page_dict.get("blocks", []):
            for line in blk.get("lines", []):
                for span in line.get("spans", []):
                    sizes.append(span.get("size", 0.0))
    body_size = _median(sizes) if sizes else 11.0

    ocr_available = _ocr.is_tesseract_available()
    ocr_pages_done = 0
    ocr_pages_skipped = 0
    page_count = len(doc)

    for page_index, page in enumerate(doc):
        if page_index >= 1000:
            warnings.append("PDF truncated to first 1000 pages.")
            break

        native_blocks = _extract_native_blocks(page, body_size)
        native_alpha = sum(sum(c.isalpha() for c in b.text) for b in native_blocks)

        if native_alpha >= NATIVE_TEXT_MIN_ALPHA_CHARS:
            blocks.extend(native_blocks)
        else:
            # Treat as a scanned page → OCR.
            if not ocr_available:
                ocr_pages_skipped += 1
                continue
            if ocr_pages_done >= _ocr.MAX_OCR_PAGES:
                ocr_pages_skipped += 1
                continue
            try:
                ocr_blocks = _ocr_page(page)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OCR failed on page %d: %s", page_index + 1, exc)
                ocr_blocks = []
            if ocr_blocks:
                blocks.extend(ocr_blocks)
                ocr_pages_done += 1

        blocks.append(Block(type="spacer"))

    # Warnings — only surface if they are actionable for the user.
    if ocr_pages_done > 0:
        warnings.append(
            f"OCR appliqué à {ocr_pages_done} page(s) sur {page_count} (texte non sélectionnable détecté)."
        )
    if ocr_pages_skipped > 0 and not ocr_available:
        warnings.append(
            "Ce PDF semble être un scan, mais Tesseract n'est pas installé sur le serveur — "
            "le texte n'a pas pu être extrait. Installe `tesseract-ocr` et relance."
        )
    elif ocr_pages_skipped > 0:
        warnings.append(
            f"OCR limité à {_ocr.MAX_OCR_PAGES} pages ; {ocr_pages_skipped} page(s) scan ignorée(s)."
        )

    if not blocks or all(b.type == "spacer" or not b.text for b in blocks):
        warnings.append(
            "Aucun texte extractible — ni texte natif, ni OCR. Vérifie que le fichier "
            "n'est pas vide ou crypté."
        )

    return blocks, warnings


def _extract_native_blocks(page: fitz.Page, body_size: float) -> list[Block]:
    """Pull text blocks from PyMuPDF's `dict` view, classifying headings by size."""
    out: list[Block] = []
    page_dict = page.get_text("dict")
    for blk in page_dict.get("blocks", []):
        if blk.get("type") != 0:
            continue
        paragraph_parts: list[str] = []
        paragraph_max_size = 0.0
        for line in blk.get("lines", []):
            line_parts: list[str] = []
            for span in line.get("spans", []):
                span_text = span.get("text", "")
                if not span_text:
                    continue
                line_parts.append(span_text)
                paragraph_max_size = max(paragraph_max_size, span.get("size", 0.0))
            if line_parts:
                paragraph_parts.append("".join(line_parts))
        paragraph = " ".join(p.strip() for p in paragraph_parts).strip()
        if not paragraph:
            continue

        if paragraph_max_size > body_size * 1.25 and len(paragraph) < 200:
            level = 1 if paragraph_max_size > body_size * 1.6 else 2
            out.append(Block(type="heading", text=paragraph, level=level))
        else:
            out.append(Block(type="paragraph", text=paragraph))
    return out


def _ocr_page(page: fitz.Page) -> list[Block]:
    """Rasterize a single page and OCR it. Returns paragraph blocks."""
    import io

    from PIL import Image  # type: ignore[import-untyped]

    # `Matrix(scale, scale)` controls effective DPI; 72 dpi is the PDF default,
    # so DPI / 72 gives the multiplier.
    scale = _ocr.DPI / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    result = _ocr.ocr_image(img)

    blocks: list[Block] = []
    for para in result.paragraphs:
        para = para.strip()
        if para:
            blocks.append(Block(type="paragraph", text=para))
    return blocks


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2
