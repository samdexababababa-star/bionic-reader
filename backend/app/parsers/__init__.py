"""File parsers — every supported format produces a normalized `DocumentModel`.

Parsers are imported lazily to keep cold-start memory low (each backend
parser pulls in heavy native deps such as PyMuPDF or lxml).
"""
from __future__ import annotations

import importlib
import uuid
from collections.abc import Callable
from pathlib import Path

from ..models import Block, DocumentModel

ParserFn = Callable[[bytes], tuple[list[Block], list[str]]]

# Map extension to (module name within this package, function name).
EXT_PARSER_MODULES: dict[str, tuple[str, str]] = {
    "pdf": ("pdf_parser", "parse"),
    "docx": ("docx_parser", "parse"),
    "doc": ("docx_parser", "parse"),
    "pptx": ("pptx_parser", "parse"),
    "xlsx": ("xlsx_parser", "parse"),
    "txt": ("txt_parser", "parse"),
    "md": ("md_parser", "parse"),
    "markdown": ("md_parser", "parse"),
    "html": ("html_parser", "parse"),
    "htm": ("html_parser", "parse"),
    "epub": ("epub_parser", "parse"),
    "rtf": ("rtf_parser", "parse"),
    # Image formats — OCR'd via Tesseract.
    "png": ("image_parser", "parse"),
    "jpg": ("image_parser", "parse"),
    "jpeg": ("image_parser", "parse"),
    "tif": ("image_parser", "parse"),
    "tiff": ("image_parser", "parse"),
    "bmp": ("image_parser", "parse"),
    "webp": ("image_parser", "parse"),
}

SUPPORTED_EXTENSIONS = sorted(EXT_PARSER_MODULES.keys())


def _load(ext: str) -> ParserFn:
    mod_name, fn_name = EXT_PARSER_MODULES[ext]
    module = importlib.import_module(f".{mod_name}", package=__name__)
    fn = getattr(module, fn_name)
    return fn  # type: ignore[no-any-return]


def parse_bytes(filename: str, data: bytes) -> DocumentModel:
    """Dispatch to the right parser based on filename extension."""
    ext = Path(filename).suffix.lower().lstrip(".") or "txt"
    if ext not in EXT_PARSER_MODULES:
        ext = "txt"
    parser_fn = _load(ext)
    blocks, warnings = parser_fn(data)

    text_total = "\n".join(b.text for b in blocks)
    return DocumentModel(
        id=str(uuid.uuid4()),
        filename=filename,
        format=ext,
        word_count=len([w for w in text_total.split() if w]),
        char_count=len(text_total),
        blocks=blocks,
        warnings=warnings,
    )
