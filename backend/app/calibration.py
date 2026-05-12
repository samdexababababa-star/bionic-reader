"""Calibration backend for the guided-mode v2 onboarding.

The frontend collects three streams of data during onboarding:

1. **ASRS-v1.1 Part A** — the WHO-validated 6-question Adult ADHD
   Self-Report Scale screener (Kessler et al., *Psychol Med* 2005). It
   classifies each answer on a 0–4 Likert scale (Jamais → Très souvent).
   The standard scoring threshold is **≥ 4 darkened cells** out of 6,
   where "darkened" means the answer falls within a per-item shaded
   region. We replicate the exact shaded regions from the WHO instrument.

2. **PVT (Psychomotor Vigilance Task)** — 12-16 trials, each measuring
   reaction time to a visual stimulus appearing after a random foreperiod
   (2-10 s). Standard endpoints (Dinges & Powell, *Behav Res Methods*
   1985):
       - mean RT (ms)
       - lapses: trials with RT > 500 ms
       - false starts: clicks before stimulus

3. **Short reading test** — the user reads ~60 words and clicks "done".
   We compute reading WPM (with a sanity floor / ceiling).

These three streams feed a small **multi-dimensional model** (no ML —
just well-documented heuristics derived from the cited literature) that
returns:

    - Four normalised affinities to the four presets (apaisé / équilibré /
      concentré / sprint) summing to 1.0
    - The recommended preset (argmax)
    - Five interpretable dimensions on a 0..1 scale: inattention,
      hyperactivity_impulsivity, working_memory, processing_speed,
      distraction_sensitivity
    - A natural-language rationale ("Détecté : tendance inattentive,
      vigilance moyenne. Réglage suggéré : ...")
    - A confidence between 0.1 and 1.0 reflecting how much data the user
      actually provided (skipping the PVT or the reading test reduces
      confidence accordingly).

Why a transparent linear model instead of ML?
---------------------------------------------
ML models with N=1 are noise. ASRS scoring is itself a hand-crafted linear
rule with documented validity and the user benefits from *understanding*
why the system suggested what it did.

References
----------
- Kessler RC et al. *Psychol Med* 2005;35:245-256
- Adler LA et al. *Ann Clin Psychiatry* 2006;18(3):145-148
- Dinges DF, Powell JW. *Behav Res Methods Instrum Comput* 1985;17:652-655
- Solanto MV et al. *J Abnorm Child Psychol* 2001;29:215-228
- Castellanos FX, Sonuga-Barke EJS, Milham MP, Tannock R.
  *Trends Cogn Sci* 2006;10:117-123
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Profile = Literal["apaise", "equilibre", "concentre", "sprint"]


class ASRSResponse(BaseModel):
    """A single ASRS-v1.1 Part A response.

    `value` is 0 (Jamais) .. 4 (Très souvent).
    `question_id` is 1..6 matching the WHO instrument order.
    """

    question_id: int = Field(ge=1, le=6)
    value: int = Field(ge=0, le=4)


class PVTResult(BaseModel):
    """Aggregated results of the in-browser PVT."""

    mean_rt_ms: float | None = Field(default=None, ge=80.0, le=2000.0)
    median_rt_ms: float | None = Field(default=None, ge=80.0, le=2000.0)
    lapses: int = Field(default=0, ge=0)  # trials with RT > 500 ms
    false_starts: int = Field(default=0, ge=0)
    trials: int = Field(default=0, ge=0)


class ReadingTestResult(BaseModel):
    """Outcome of the short reading task."""

    words: int = Field(default=0, ge=0)
    elapsed_ms: float = Field(default=0.0, ge=0.0)
    self_reported_difficulty: int | None = Field(default=None, ge=0, le=4)


class CalibrationRequest(BaseModel):
    asrs: list[ASRSResponse] = Field(default_factory=list)
    pvt: PVTResult | None = None
    reading: ReadingTestResult | None = None


class Dimensions(BaseModel):
    inattention: float = Field(ge=0.0, le=1.0)
    hyperactivity_impulsivity: float = Field(ge=0.0, le=1.0)
    working_memory: float = Field(ge=0.0, le=1.0)
    processing_speed: float = Field(ge=0.0, le=1.0)
    distraction_sensitivity: float = Field(ge=0.0, le=1.0)


class Affinities(BaseModel):
    apaise: float = Field(ge=0.0, le=1.0)
    equilibre: float = Field(ge=0.0, le=1.0)
    concentre: float = Field(ge=0.0, le=1.0)
    sprint: float = Field(ge=0.0, le=1.0)


class CalibrationResult(BaseModel):
    profile: Profile
    affinities: Affinities
    dimensions: Dimensions
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    asrs_positive: bool
    reading_wpm: float | None = None


# ---------------------------------------------------------------------------
# ASRS-v1.1 Part A scoring
# ---------------------------------------------------------------------------
#
# Source: Kessler et al. 2005 — for each of the 6 items, a response is
# considered "darkened" (= clinically meaningful) if it falls at or above
# the threshold below. The 4 first questions use the threshold "Parfois (2)"
# and the 2 last use "Souvent (3)".
#
# These exact thresholds match the WHO scoring sheet.
ASRS_DARKENED_THRESHOLDS = {1: 2, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3}


def asrs_score(responses: list[ASRSResponse]) -> tuple[int, int, bool]:
    """Return `(darkened_count, raw_total, is_positive_screen)`.

    `is_positive_screen` follows the WHO rule: ≥ 4 of 6 items darkened.
    """
    darkened = 0
    raw_total = 0
    seen: set[int] = set()
    for r in responses:
        if r.question_id in seen:
            continue
        seen.add(r.question_id)
        threshold = ASRS_DARKENED_THRESHOLDS.get(r.question_id)
        if threshold is None:
            continue
        raw_total += r.value
        if r.value >= threshold:
            darkened += 1
    return darkened, raw_total, darkened >= 4


# ---------------------------------------------------------------------------
# Dimensional model
# ---------------------------------------------------------------------------


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pvt_dimensions(pvt: PVTResult | None) -> tuple[float, float, float]:
    """Return (processing_speed, distraction_sensitivity, hyper_impulsivity_pvt).

    Calibrated on Dinges & Powell 1985 norms for adults:
        - Healthy mean RT: 250-290 ms
        - Mildly slow / sleepy: 300-360 ms
        - ADHD-typical: variable RT, mean often 330-400 ms, lapse rate ↑
        - Lapse-prone (n_lapses > ~3 / 20 trials) is a strong marker
    """
    if pvt is None or (pvt.median_rt_ms is None and pvt.mean_rt_ms is None):
        # No PVT data — return neutral midpoints.
        return 0.5, 0.5, 0.3

    rt = pvt.median_rt_ms or pvt.mean_rt_ms or 320.0

    # Processing speed: fast RT = high speed. Map [220 ms → 1.0, 500 ms → 0.0].
    speed = _clamp01(1.0 - (rt - 220.0) / 280.0)

    # Distraction sensitivity from lapse rate. Each lapse over baseline (1 / 20)
    # adds ~0.15.
    trials = max(1, pvt.trials)
    expected_baseline_lapses = trials / 20.0
    excess_lapses = max(0.0, pvt.lapses - expected_baseline_lapses)
    distraction = _clamp01(0.25 + 0.12 * excess_lapses)

    # Hyper-impulsive PVT signature: many false starts (Solanto 2001).
    hyper_impuls = _clamp01(0.15 + 0.18 * pvt.false_starts)

    return speed, distraction, hyper_impuls


def _reading_dimensions(reading: ReadingTestResult | None) -> tuple[float | None, float]:
    """Return (reading_wpm, working_memory).

    Working memory is partly inferred from self-reported difficulty during
    the reading test; full WM measurement (Corsi / digit span) is out of
    scope for a 90-second onboarding.
    """
    if reading is None or reading.elapsed_ms <= 0 or reading.words <= 0:
        return None, 0.5

    minutes = reading.elapsed_ms / 60_000.0
    wpm = reading.words / minutes if minutes > 0 else 0.0
    wpm = max(40.0, min(900.0, wpm))  # sanity clip — reject pathological extremes

    # Self-reported difficulty 0..4 → working memory 0.85..0.25
    if reading.self_reported_difficulty is not None:
        wm = _clamp01(0.85 - reading.self_reported_difficulty * 0.15)
    else:
        # Slower reading correlates weakly with WM load.
        # Map [180 wpm → 0.4, 320 wpm → 0.75].
        wm = _clamp01(0.4 + (wpm - 180) / 280.0 * 0.35)

    return wpm, wm


def _profile_affinities(dim: Dimensions, asrs_positive: bool) -> Affinities:
    """Score the four presets given the five dimensions.

    The four presets exist for a reason — they map to the cognitive sub-types
    we see in ADHD-adjacent users:

    - **apaise**: inattentive + visually fatigued readers (long calm sessions,
      low salience, focus on parchment-style typography).
    - **equilibre**: generalist, mid-range on every axis.
    - **concentre**: high inattention but motivated for dense study; needs
      strong focus mode + phrase chunking + pulse cadence.
    - **sprint**: high impulsivity + processing-speed surplus; RSVP scanning.
    """
    apaise = (
        0.35
        + 0.40 * dim.inattention
        + 0.25 * dim.distraction_sensitivity
        - 0.20 * dim.processing_speed
        - 0.15 * dim.hyperactivity_impulsivity
        + (0.10 if asrs_positive else 0.0)
    )
    equilibre = (
        0.55
        - 0.15 * abs(dim.inattention - 0.5)
        - 0.15 * abs(dim.hyperactivity_impulsivity - 0.5)
        - 0.10 * abs(dim.processing_speed - 0.5)
    )
    concentre = (
        0.30
        + 0.30 * dim.inattention
        + 0.30 * (1 - dim.working_memory)
        + 0.15 * dim.distraction_sensitivity
        - 0.10 * dim.hyperactivity_impulsivity
    )
    sprint = (
        0.20
        + 0.45 * dim.hyperactivity_impulsivity
        + 0.30 * dim.processing_speed
        - 0.20 * dim.distraction_sensitivity
        - 0.10 * dim.inattention
    )

    raw = {
        "apaise": max(0.0, apaise),
        "equilibre": max(0.0, equilibre),
        "concentre": max(0.0, concentre),
        "sprint": max(0.0, sprint),
    }
    total = sum(raw.values()) or 1.0
    return Affinities(
        apaise=raw["apaise"] / total,
        equilibre=raw["equilibre"] / total,
        concentre=raw["concentre"] / total,
        sprint=raw["sprint"] / total,
    )


def _confidence(req: CalibrationRequest) -> float:
    """How much data did the user actually give us?

    100% confidence requires all 6 ASRS + PVT + reading test.
    """
    contrib = 0.0
    contrib += 0.10 * min(6, len(req.asrs)) / 6  # 10% for ASRS
    contrib += 0.40 if req.pvt and req.pvt.trials >= 8 else 0.10 if req.pvt else 0.0
    contrib += 0.40 if req.reading and req.reading.words >= 30 else 0.10 if req.reading else 0.0
    contrib += 0.10  # base confidence from the user even running the wizard
    return _clamp01(contrib)


def _rationale(
    dim: Dimensions,
    affinities: Affinities,
    profile: Profile,
    asrs_positive: bool,
    reading_wpm: float | None,
) -> str:
    """Build a one-paragraph natural-language explanation."""
    detected: list[str] = []
    if asrs_positive:
        detected.append("score ASRS positif (≥ 4 / 6)")
    if dim.inattention >= 0.7:
        detected.append("tendance inattentive marquée")
    elif dim.inattention >= 0.55:
        detected.append("attention sélective fragile")
    if dim.hyperactivity_impulsivity >= 0.65:
        detected.append("impulsivité élevée (faux départs PVT)")
    if dim.distraction_sensitivity >= 0.6:
        detected.append("sensibilité aux distractions (lapses)")
    if dim.processing_speed >= 0.75:
        detected.append("vitesse de traitement élevée")
    elif dim.processing_speed <= 0.35:
        detected.append("vitesse de traitement plus lente")
    if reading_wpm:
        detected.append(f"vitesse de lecture mesurée ~{int(reading_wpm)} mots/min")

    setting_msg = {
        "apaise": "fond parchemin doux, bionique discret 35 %, focus paragraphe fort, OVP visible — pour lire longtemps sans fatigue",
        "equilibre": "réglage généraliste, bionique 45 %, focus paragraphe modéré — bon réflexe par défaut",
        "concentre": "fond gris froid, bionique 50 %, phrase chunking + pulse cadence, focus paragraphe 90 % — pour les textes denses",
        "sprint": "mode RSVP 350 mots/min, un mot à la fois, pauses sur ponctuation — pour scanner vite",
    }[profile]

    detected_str = ", ".join(detected) if detected else "aucun marqueur fort"
    return f"Détecté : {detected_str}. Réglage suggéré : {setting_msg}."


def calibrate(req: CalibrationRequest) -> CalibrationResult:
    """The single entry-point used by `/api/profile/calibrate`."""
    darkened, _, asrs_positive = asrs_score(req.asrs)

    # ASRS inattention items are 1-4, hyperactivity-impulsivity are 5-6.
    asrs_inattention_raw = 0
    asrs_hyper_raw = 0
    seen: set[int] = set()
    for r in req.asrs:
        if r.question_id in seen:
            continue
        seen.add(r.question_id)
        if r.question_id <= 4:
            asrs_inattention_raw += r.value
        else:
            asrs_hyper_raw += r.value

    inatt_norm = _clamp01(asrs_inattention_raw / 16.0)  # 4 items × 4 max
    hyper_norm = _clamp01(asrs_hyper_raw / 8.0)        # 2 items × 4 max

    speed, distraction_pvt, hyper_impuls_pvt = _pvt_dimensions(req.pvt)
    reading_wpm, working_memory = _reading_dimensions(req.reading)

    dimensions = Dimensions(
        inattention=_clamp01(0.5 * inatt_norm + 0.3 * distraction_pvt + 0.2 * (1 - speed)),
        hyperactivity_impulsivity=_clamp01(0.6 * hyper_norm + 0.4 * hyper_impuls_pvt),
        working_memory=working_memory,
        processing_speed=speed,
        distraction_sensitivity=distraction_pvt,
    )

    affinities = _profile_affinities(dimensions, asrs_positive)
    profile_choice: Profile = max(
        ("apaise", "equilibre", "concentre", "sprint"),
        key=lambda p: getattr(affinities, p),
    )  # type: ignore[assignment]
    rationale = _rationale(dimensions, affinities, profile_choice, asrs_positive, reading_wpm)
    confidence = _confidence(req)

    return CalibrationResult(
        profile=profile_choice,
        affinities=affinities,
        dimensions=dimensions,
        rationale=rationale,
        confidence=confidence,
        asrs_positive=asrs_positive,
        reading_wpm=reading_wpm,
    )
