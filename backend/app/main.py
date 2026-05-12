"""FastAPI entrypoint for Bionic Reader Pro."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import quantum
from .calibration import CalibrationRequest, CalibrationResult, calibrate
from .exporters import SUPPORTED_EXPORTS, get_exporter
from .inplace import SUPPORTED_INPLACE, get_inplace_exporter
from .models import BionicSettings, ExportRequest
from .parsers import SUPPORTED_EXTENSIONS, parse_bytes

logger = logging.getLogger("bionic_reader")
logging.basicConfig(level=logging.INFO)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

app = FastAPI(
    title="Bionic Reader Pro API",
    version="0.1.0",
    description="Convert PDF/DOCX/TXT/EPUB/HTML/MD/RTF into ADHD-friendly bionic reading format.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "supported_extensions": SUPPORTED_EXTENSIONS}


@app.get("/api/formats")
def formats() -> dict[str, list[str]]:
    return {
        "input": SUPPORTED_EXTENSIONS,
        "output": SUPPORTED_EXPORTS,
        "inplace": SUPPORTED_INPLACE,
    }


@app.post("/api/parse")
async def parse(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large; max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    try:
        document = parse_bytes(file.filename or "untitled.txt", data)
    except Exception as exc:
        logger.exception("parse failed")
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {exc}") from exc
    return document


@app.post("/api/export")
def export(req: ExportRequest):
    fmt = req.format
    if fmt not in SUPPORTED_EXPORTS:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")
    exporter = get_exporter(fmt)
    try:
        body, media_type, filename = exporter(req.document, req.settings, req.title)
    except Exception as exc:
        logger.exception("export failed")
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/export-inplace")
async def export_inplace(
    file: UploadFile = File(..., description="Original file bytes to transform in-place."),
    settings: str = Form(..., description="BionicSettings as JSON string."),
):
    """Apply bionic transformation directly on the user's original file.

    Preserves images, tables, charts, embedded objects, fonts, colors,
    hyperlinks, headers/footers, formulas (XLSX), animations (PPTX), and
    the overall document structure. Only word-prefix text content is
    styled in bold. The original file is never written to disk on the
    server.

    Supported source formats: DOCX, PDF, PPTX, XLSX. The output always
    matches the source format.
    """
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    ext = Path(file.filename or "document").suffix.lower().lstrip(".")
    if ext not in SUPPORTED_INPLACE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"In-place export not supported for .{ext} files. "
                f"Supported: {', '.join(SUPPORTED_INPLACE)}."
            ),
        )

    try:
        settings_obj = BionicSettings(**json.loads(settings))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid settings JSON: {exc}") from exc

    exporter = get_inplace_exporter(ext)
    try:
        body, media_type, filename = exporter(data, settings_obj, file.filename or f"document.{ext}")
    except Exception as exc:
        logger.exception("inplace export failed")
        raise HTTPException(status_code=500, detail=f"In-place export failed: {exc}") from exc

    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Guided-mode v2 onboarding calibration
# ---------------------------------------------------------------------------
@app.post("/api/profile/calibrate", response_model=CalibrationResult)
def profile_calibrate(req: CalibrationRequest) -> CalibrationResult:
    """Score the guided-mode v2 wizard responses.

    Combines the ASRS-v1.1 screener, the PVT vigilance task, and the
    short reading test into a recommended `ReadingProfile` plus
    interpretable dimensional metrics and a natural-language rationale.
    See `app/calibration.py` for the full design + literature notes.
    """
    return calibrate(req)


# ---------------------------------------------------------------------------
# Intention Studio (wave / quantum-entropy emitter & receiver)
# ---------------------------------------------------------------------------
@app.post("/api/wave/emit", response_model=quantum.WaveSignal)
async def wave_emit(req: quantum.EmitRequest) -> quantum.WaveSignal:
    """Send an intention. Returns a quantum-entropy-derived `WaveSignal`."""
    return await quantum.emit(req)


@app.post("/api/wave/receive", response_model=quantum.WaveSignal)
async def wave_receive(req: quantum.ReceiveRequest) -> quantum.WaveSignal:
    """Pull a signal. Returns a quantum-entropy-derived `WaveSignal`."""
    return await quantum.receive(req)


@app.get("/api/wave/status")
def wave_status() -> dict[str, object]:
    """Diagnostic: which entropy / LLM sources are configured."""
    return {
        "qrng_endpoint": quantum.ANU_URL,
        "llm_enabled": bool(os.environ.get("MISTRAL_API_KEY")),
        "llm_model": quantum.MISTRAL_MODEL,
        "archetypes": len(quantum.ARCHETYPES),
    }
