"""OCR (Optical Character Recognition) helpers shared between parsers.

We use **Tesseract** (via `pytesseract`) as the primary engine — it is the
only OCR engine that ships as a system package on every major Linux distro,
in Homebrew, and as a Windows installer. It is also the only major engine
that does NOT require pulling in a 1+ GB ML model on first use, which would
break the cold-start budget of this app.

Language handling
-----------------
Tesseract uses 3-letter ISO codes joined with `+` for multi-language input.
We try `fra+eng` by default (the user is French-speaking) and gracefully
degrade to `eng` if French is not installed.

Confidence filtering
--------------------
Tesseract's `image_to_data` returns a confidence (0–100) per word.
We drop anything below `CONFIDENCE_THRESHOLD` (default 50) so the output
is selectable / searchable text rather than mojibake.

Performance
-----------
Each PDF page is rasterized at 220 DPI (a good lisibility / speed
trade-off — 300 DPI gives marginal accuracy gains for ~2× the runtime).
We cap a single document at `MAX_OCR_PAGES` pages to avoid stalling the
event loop on a 1000-page scan; the user gets a clear warning if their
document is truncated.

Why not PaddleOCR / docTR / EasyOCR?
------------------------------------
All three give better raw accuracy on noisy / handwritten / rotated text,
but:
- they pull 500 MB – 1.5 GB of model weights on first run,
- they require PyTorch or PaddlePaddle (heavyweight),
- they break completely without GPU on long documents.

Tesseract 4.1+ uses an LSTM backend and is on-par with EasyOCR for clean
printed material, which is the dominant scanned-document case for ADHD
readers who upload PDFs of articles, slides, and textbook pages.

If a future iteration wants the very best raw accuracy, the entry point
is `_run_tesseract` — swap it for a `_run_paddle` or `_run_doctr` keeping
the same return contract.
"""
from __future__ import annotations

import io
import logging
import shutil
from dataclasses import dataclass

from PIL import Image  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES = "fra+eng"
FALLBACK_LANGUAGE = "eng"
CONFIDENCE_THRESHOLD = 50
DPI = 220
MAX_OCR_PAGES = 200


@dataclass
class OcrWord:
    """A single OCR-recognized word with its bounding box and confidence."""

    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int
    line_id: int  # words that share a line share this id

    @property
    def baseline_y(self) -> int:
        """Approximate baseline (bottom of the bbox)."""
        return self.y + self.height


@dataclass
class OcrPage:
    """OCR output for a single page / image."""

    words: list[OcrWord]
    lines: list[str]
    paragraphs: list[str]
    mean_confidence: float


def is_tesseract_available() -> bool:
    """Return True if a Tesseract binary is found on PATH."""
    return shutil.which("tesseract") is not None


def _available_languages() -> set[str]:
    """Return the set of installed Tesseract language packs (3-letter codes)."""
    if not is_tesseract_available():
        return set()
    try:
        import pytesseract  # type: ignore[import-untyped]

        langs = pytesseract.get_languages(config="")
        return set(langs)
    except Exception:  # noqa: BLE001
        return set()


def _resolve_languages(requested: str = DEFAULT_LANGUAGES) -> str:
    """Filter `requested` (e.g. `fra+eng`) down to packs that are installed.

    Always returns at least `eng`, since that is bundled with every
    `tesseract-ocr` install.
    """
    available = _available_languages()
    if not available:
        return FALLBACK_LANGUAGE
    parts = [p for p in requested.split("+") if p in available]
    if not parts:
        return FALLBACK_LANGUAGE
    return "+".join(parts)


def ocr_image(image: Image.Image, languages: str = DEFAULT_LANGUAGES) -> OcrPage:
    """Run OCR on a PIL Image and return structured text + bounding boxes.

    The image should be at the rendering DPI you want Tesseract to assume
    (we render at `DPI` for PDFs). Pre-binarization is **not** applied —
    Tesseract 4 (LSTM) handles grayscale and color directly and is usually
    hurt by aggressive thresholding on antialiased fonts.
    """
    import pytesseract  # type: ignore[import-untyped]
    from pytesseract import Output  # type: ignore[import-untyped]

    langs = _resolve_languages(languages)
    # `--psm 3` = fully automatic page segmentation (default).
    # `--oem 1` = LSTM only (more accurate than legacy or combined).
    config = "--psm 3 --oem 1"
    data = pytesseract.image_to_data(image, lang=langs, config=config, output_type=Output.DICT)

    n = len(data.get("text", []))
    words: list[OcrWord] = []
    confidences: list[float] = []
    line_buckets: dict[tuple[int, int, int, int], list[OcrWord]] = {}
    para_buckets: dict[tuple[int, int, int], list[OcrWord]] = {}

    for i in range(n):
        raw_text = (data["text"][i] or "").strip()
        if not raw_text:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < CONFIDENCE_THRESHOLD:
            continue
        try:
            x = int(data["left"][i])
            y = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])
        except (TypeError, ValueError, KeyError):
            continue
        block_num = int(data.get("block_num", [0] * n)[i])
        par_num = int(data.get("par_num", [0] * n)[i])
        line_num = int(data.get("line_num", [0] * n)[i])
        line_key = (int(data.get("page_num", [0] * n)[i]), block_num, par_num, line_num)
        para_key = (int(data.get("page_num", [0] * n)[i]), block_num, par_num)

        word = OcrWord(
            text=raw_text,
            confidence=conf,
            x=x,
            y=y,
            width=w,
            height=h,
            line_id=hash(line_key) & 0xFFFFFFFF,
        )
        words.append(word)
        confidences.append(conf)
        line_buckets.setdefault(line_key, []).append(word)
        para_buckets.setdefault(para_key, []).append(word)

    # Rebuild lines and paragraphs in reading order (top-to-bottom, left-to-right).
    lines: list[str] = []
    for key in sorted(line_buckets.keys()):
        line_words = sorted(line_buckets[key], key=lambda w: w.x)
        lines.append(" ".join(w.text for w in line_words))

    paragraphs: list[str] = []
    for key in sorted(para_buckets.keys()):
        para_words = sorted(para_buckets[key], key=lambda w: (w.y, w.x))
        # Group by line again to keep newlines / spaces between lines coherent.
        para_lines: dict[int, list[OcrWord]] = {}
        for w in para_words:
            para_lines.setdefault(w.line_id, []).append(w)
        line_texts = [
            " ".join(ww.text for ww in sorted(para_lines[lid], key=lambda x: x.x))
            for lid in sorted(para_lines.keys(), key=lambda lid: min(ww.y for ww in para_lines[lid]))
        ]
        paragraphs.append(" ".join(line_texts))

    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return OcrPage(words=words, lines=lines, paragraphs=paragraphs, mean_confidence=mean_conf)


def ocr_bytes(data: bytes, languages: str = DEFAULT_LANGUAGES) -> OcrPage:
    """Run OCR on raw image bytes (PNG/JPG/etc)."""
    img = Image.open(io.BytesIO(data))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return ocr_image(img, languages=languages)
