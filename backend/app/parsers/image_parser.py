"""Image parser — runs OCR on uploaded PNG/JPG/etc. images.

Returns paragraph blocks reconstructed from Tesseract's per-word boxes.
This is what makes the app actually useful when a user has a photo of a
page they want to read — typical ADHD-friendly scenario.
"""
from __future__ import annotations

import logging

from ..models import Block
from . import _ocr

logger = logging.getLogger(__name__)


def parse(data: bytes) -> tuple[list[Block], list[str]]:
    warnings: list[str] = []
    blocks: list[Block] = []

    if not _ocr.is_tesseract_available():
        warnings.append(
            "Cette image nécessite l'OCR, mais Tesseract n'est pas installé sur le serveur."
        )
        return blocks, warnings

    try:
        result = _ocr.ocr_bytes(data)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Image OCR failed")
        warnings.append(f"OCR failed on image: {exc}")
        return blocks, warnings

    for para in result.paragraphs:
        para = para.strip()
        if para:
            blocks.append(Block(type="paragraph", text=para))

    if not blocks:
        warnings.append(
            "Aucun texte détecté dans l'image. Vérifie qu'elle contient du texte "
            "lisible (au moins ~12 px de hauteur de lettre)."
        )
    else:
        warnings.append(
            f"OCR appliqué (confiance moyenne : {result.mean_confidence:.0f}/100)."
        )
    return blocks, warnings
