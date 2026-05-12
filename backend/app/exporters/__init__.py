"""Document exporters — produce a NEW file in the requested format.

The original uploaded file is never written to disk and never modified.
Each exporter takes a normalized `DocumentModel` plus `BionicSettings`
and returns (bytes, content-type, filename) for download.

Lazy-loaded to keep cold start light.
"""
from __future__ import annotations

import importlib
from collections.abc import Callable

from ..models import BionicSettings, DocumentModel

ExporterFn = Callable[[DocumentModel, BionicSettings, str | None], tuple[bytes, str, str]]

EXPORTER_MODULES: dict[str, tuple[str, str]] = {
    "html": ("html_exporter", "export"),
    "docx": ("docx_exporter", "export"),
    "txt": ("txt_exporter", "export"),
}

SUPPORTED_EXPORTS = sorted(EXPORTER_MODULES.keys())


def get_exporter(fmt: str) -> ExporterFn:
    if fmt not in EXPORTER_MODULES:
        raise KeyError(fmt)
    mod_name, fn_name = EXPORTER_MODULES[fmt]
    module = importlib.import_module(f".{mod_name}", package=__name__)
    fn = getattr(module, fn_name)
    return fn  # type: ignore[no-any-return]
