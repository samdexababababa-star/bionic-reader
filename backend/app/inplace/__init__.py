"""In-place exporters — preserve document fidelity.

Unlike `app/exporters/*` which rebuild a fresh document from a parsed
DocumentModel (loses images, tables, headers, styles, embedded objects),
these exporters open the user's *original* file and apply bionic styling
at the run / glyph level.

What stays intact:
- DOCX : images, tables, headers/footers, comments, styles, fonts, colors,
        hyperlinks, footnotes, sections, page setup, embedded objects.
- PDF  : images, vectors, signatures, annotations, page count, metadata,
        font resources. Only prefix-letter regions are re-rendered in bold.
- PPTX : layouts, themes, images, tables, charts, animations, slide masters.
- XLSX : formulas, charts, images, named ranges, conditional formatting,
        cell styles. Formula cells are never touched.
"""
from __future__ import annotations

import importlib
from collections.abc import Callable

from ..models import BionicSettings

InPlaceFn = Callable[[bytes, BionicSettings, str], tuple[bytes, str, str]]

INPLACE_MODULES: dict[str, tuple[str, str]] = {
    "docx": ("docx_inplace", "export_inplace"),
    "pdf": ("pdf_inplace", "export_inplace"),
    "pptx": ("pptx_inplace", "export_inplace"),
    "xlsx": ("xlsx_inplace", "export_inplace"),
}

SUPPORTED_INPLACE = sorted(INPLACE_MODULES.keys())


def get_inplace_exporter(fmt: str) -> InPlaceFn:
    if fmt not in INPLACE_MODULES:
        raise KeyError(fmt)
    mod_name, fn_name = INPLACE_MODULES[fmt]
    module = importlib.import_module(f".{mod_name}", package=__name__)
    fn = getattr(module, fn_name)
    return fn  # type: ignore[no-any-return]
