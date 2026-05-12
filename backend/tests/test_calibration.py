"""Tests for the guided-mode v2 calibration logic.

We pick canonical user profiles from the literature (Solanto 2001 sub-type
prototypes, Castellanos 2006 RT-variability profile) and assert the scorer
maps them to the correct preset with a sensible rationale.
"""
from __future__ import annotations

from app.calibration import (
    ASRSResponse,
    CalibrationRequest,
    PVTResult,
    ReadingTestResult,
    asrs_score,
    calibrate,
)


def _asrs(values: list[int]) -> list[ASRSResponse]:
    return [ASRSResponse(question_id=i + 1, value=v) for i, v in enumerate(values)]


def test_asrs_screen_positive() -> None:
    # Pattern matching the canonical "positive screen": items 1-4 ≥ 2, items 5-6 ≥ 3.
    darkened, _, positive = asrs_score(_asrs([3, 3, 3, 2, 3, 3]))
    assert darkened == 6
    assert positive is True


def test_asrs_screen_negative() -> None:
    # All "Rarement" — no darkened cells anywhere.
    darkened, _, positive = asrs_score(_asrs([1, 1, 1, 1, 1, 1]))
    assert darkened == 0
    assert positive is False


def test_inattentive_subtype_maps_to_calm_or_focused() -> None:
    """High inattention + slow PVT + moderate reading should map to apaise or concentre."""
    req = CalibrationRequest(
        asrs=_asrs([3, 3, 3, 2, 0, 1]),
        pvt=PVTResult(
            median_rt_ms=380.0,
            mean_rt_ms=410.0,
            lapses=3,
            false_starts=0,
            trials=12,
        ),
        reading=ReadingTestResult(words=60, elapsed_ms=22_000, self_reported_difficulty=2),
    )
    r = calibrate(req)
    assert r.profile in {"apaise", "concentre"}
    assert r.asrs_positive is True
    assert r.dimensions.inattention >= 0.5
    assert "ASRS" in r.rationale or "inattent" in r.rationale.lower()


def test_hyperactive_impulsive_maps_to_sprint() -> None:
    """High impulsivity + fast PVT + fast reading should map to sprint."""
    req = CalibrationRequest(
        asrs=_asrs([1, 1, 2, 1, 3, 3]),
        pvt=PVTResult(
            median_rt_ms=240.0,
            mean_rt_ms=255.0,
            lapses=0,
            false_starts=2,
            trials=12,
        ),
        reading=ReadingTestResult(words=60, elapsed_ms=14_000, self_reported_difficulty=0),
    )
    r = calibrate(req)
    assert r.profile == "sprint"
    assert r.dimensions.hyperactivity_impulsivity >= 0.4


def test_neurotypical_maps_to_equilibre() -> None:
    """Mid-range on everything should map to équilibré with high confidence."""
    req = CalibrationRequest(
        asrs=_asrs([1, 2, 1, 1, 1, 1]),
        pvt=PVTResult(
            median_rt_ms=290.0,
            mean_rt_ms=300.0,
            lapses=0,
            false_starts=0,
            trials=12,
        ),
        reading=ReadingTestResult(words=60, elapsed_ms=18_000, self_reported_difficulty=1),
    )
    r = calibrate(req)
    # Mid-range users should never land on the high-arousal Sprint preset.
    assert r.profile != "sprint"
    assert r.asrs_positive is False


def test_skip_all_gives_low_confidence() -> None:
    req = CalibrationRequest(asrs=[], pvt=None, reading=None)
    r = calibrate(req)
    assert r.confidence <= 0.15  # base contribution only
    assert r.profile in {"apaise", "equilibre", "concentre", "sprint"}


def test_full_data_gives_full_confidence() -> None:
    req = CalibrationRequest(
        asrs=_asrs([2, 2, 2, 2, 2, 2]),
        pvt=PVTResult(
            median_rt_ms=300.0,
            mean_rt_ms=300.0,
            lapses=0,
            false_starts=0,
            trials=16,
        ),
        reading=ReadingTestResult(words=60, elapsed_ms=20_000, self_reported_difficulty=1),
    )
    r = calibrate(req)
    assert r.confidence == 1.0
    affs = r.affinities
    total = affs.apaise + affs.equilibre + affs.concentre + affs.sprint
    assert abs(total - 1.0) < 0.001


def test_rationale_is_natural_language() -> None:
    req = CalibrationRequest(
        asrs=_asrs([3, 3, 3, 3, 2, 2]),
        pvt=PVTResult(
            median_rt_ms=360.0,
            mean_rt_ms=380.0,
            lapses=2,
            false_starts=1,
            trials=12,
        ),
        reading=ReadingTestResult(words=60, elapsed_ms=24_000, self_reported_difficulty=2),
    )
    r = calibrate(req)
    assert r.rationale.startswith("Détecté")
    assert "Réglage suggéré" in r.rationale
    assert len(r.rationale) < 500  # not a wall of text
