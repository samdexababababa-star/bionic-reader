"""PDF in-place bionic transformation via PyMuPDF.

Strategy (preserves images, vectors, signatures, annotations, page count,
metadata):

1. For every text page, walk `get_text("rawdict")` to get each character's
   bbox + font + size + color (`rawdict` exposes per-char data which
   `dict` does not).
2. For each word, compute the bionic prefix length and gather the bboxes
   of the *prefix characters*.
3. Add a redaction annotation on the union of those prefix bboxes.
4. Apply redactions with `images=PDF_REDACT_IMAGE_NONE` — this means images
   and vector graphics are left **completely intact** even if a redaction
   rectangle happens to touch them. Only the matching text in the
   content stream is removed.
5. Re-insert the prefix text at the same position using a Base-14 bold
   font (Helvetica-Bold by default, Times-Bold / Courier-Bold heuristics
   based on the original font name).

Why not just draw an overlay on top? Because PDF readers extract text by
content-stream order, and overlay text would cause selection / accessibility
duplicates ("ABCABC...") and copy/paste artifacts. Redaction + re-insertion
keeps each character once in the content stream — copy/paste still works,
search still works, screen readers still read the page correctly.

Limitations (documented for the user):
- Custom embedded fonts cannot be replicated exactly. We fall back to a
  Base-14 bold font (always present in every PDF reader). For most
  documents the visual difference is minor; mathematical / symbol heavy
  documents may show fallback boxes.
- Right-to-left scripts (Arabic, Hebrew) are not supported.
- Scanned PDFs (image-only, no text layer) cannot be bionic-ified
  in-place without OCR — a separate OCR pre-processing step is required
  (see `pdf_ocr_inplace`).
"""
from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF

from ..models import BionicSettings
from ..transformer import WORD_RE, _prefix_length


def export_inplace(
    data: bytes,
    settings: BionicSettings,
    filename: str = "document.pdf",
) -> tuple[bytes, str, str]:
    doc = fitz.open(stream=data, filetype="pdf")
    if settings.enabled:
        for page in doc:
            _process_page(page, settings)

    buf = io.BytesIO()
    doc.save(buf, garbage=3, deflate=True, clean=False)
    doc.close()
    stem = Path(filename).stem or "document"
    return (
        buf.getvalue(),
        "application/pdf",
        f"{stem}.bionic.pdf",
    )


def _process_page(page: fitz.Page, settings: BionicSettings) -> None:
    raw = page.get_text("rawdict")
    overlays: list[tuple[fitz.Rect, str, float, tuple[float, float, float], str]] = []

    for block in raw.get("blocks", []):
        if block.get("type", 0) != 0:
            continue  # image / drawing
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                _collect_span_overlays(span, settings, overlays)

    if not overlays:
        return

    # Step 1: redact the prefix bboxes (text layer only — images untouched).
    for rect, _, _, _, _ in overlays:
        page.add_redact_annot(rect)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

    # Step 2: reinsert each prefix in bold at its original position.
    for rect, text, fsize, color, font_hint in overlays:
        bold_fontname = _pick_bold_font(font_hint)
        # PyMuPDF baseline insertion: y must be the BASELINE, not the top.
        # Approximate baseline as bottom - descent (descent ≈ 0.18 * size).
        baseline_y = rect.y1 - max(0.5, fsize * 0.18)
        try:
            page.insert_text(
                (rect.x0, baseline_y),
                text,
                fontname=bold_fontname,
                fontsize=fsize,
                color=color,
                render_mode=0,
                overlay=True,
            )
        except Exception:
            # If insertion fails for any reason (font issues, unicode),
            # fall back to a thin underline below the prefix rect so the
            # word at least keeps SOME bionic emphasis.
            page.draw_line(
                (rect.x0, rect.y1 + 0.5),
                (rect.x1, rect.y1 + 0.5),
                color=color,
                width=0.8,
            )


def _collect_span_overlays(
    span: dict,
    settings: BionicSettings,
    out: list,
) -> None:
    chars = span.get("chars", [])
    if not chars:
        return
    font_name = span.get("font", "") or ""
    font_size = float(span.get("size", 11) or 11)
    color_int = int(span.get("color", 0))
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    color = (r, g, b)

    # Reconstruct the text string aligned with chars (one entry per char).
    text = "".join((c.get("c", "") or "") for c in chars)

    for match in WORD_RE.finditer(text):
        start, end = match.span()
        word = match.group(0)
        plen = _prefix_length(word, settings)
        if plen <= 0:
            continue
        # Guard against rawdict char-count mismatch with regex match positions.
        prefix_chars = chars[start : start + plen]
        if not prefix_chars or len(prefix_chars) != plen:
            continue

        bboxes = [pc.get("bbox") for pc in prefix_chars if pc.get("bbox")]
        if not bboxes:
            continue
        x0 = min(bb[0] for bb in bboxes)
        y0 = min(bb[1] for bb in bboxes)
        x1 = max(bb[2] for bb in bboxes)
        y1 = max(bb[3] for bb in bboxes)
        rect = fitz.Rect(x0, y0, x1, y1)
        if rect.is_empty or rect.is_infinite:
            continue
        out.append((rect, word[:plen], font_size, color, font_name))


def _pick_bold_font(fontname: str) -> str:
    n = (fontname or "").lower()
    if any(t in n for t in ("times", "serif", "roman", "garamond", "georgia", "caslon", "minion")):
        return "tibo"  # Times-Bold
    if any(t in n for t in ("mono", "courier", "consolas", "menlo", "andale")):
        return "cobo"  # Courier-Bold
    return "hebo"  # Helvetica-Bold
