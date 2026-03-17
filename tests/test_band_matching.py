"""Tests for lane alignment and band matching."""

from __future__ import annotations

import numpy as np

from biopro.plugins.western_blot.analysis.band_matching import align_lanes_by_correlation, assign_matched_bands


def _profile_with_peaks(length: int, peaks: list[int], heights: list[float]) -> np.ndarray:
    x = np.arange(length, dtype=np.float64)
    y = np.zeros(length, dtype=np.float64)
    for p, h in zip(peaks, heights):
        y += h * np.exp(-((x - p) ** 2) / (2 * 6.0**2))
    return y


def test_align_lanes_by_correlation_recovers_shift() -> None:
    length = 240
    base = _profile_with_peaks(length, [60, 120, 170], [1.0, 0.6, 0.8])
    shift = 9
    shifted = np.roll(base, shift)

    profiles = [base, shifted]
    baselines = [np.zeros_like(base), np.zeros_like(base)]
    align = align_lanes_by_correlation(profiles, baselines, ref_lane=0, max_shift_px=25)

    # We add shift_px to band position to align to ref; for a rolled-down signal,
    # alignment should apply a negative shift of approximately -shift.
    assert abs(align[1].shift_px + shift) <= 2


def test_assign_matched_bands_clusters_across_lanes() -> None:
    lane_to_band_positions = {
        0: [(0, 50.0), (1, 110.0)],
        1: [(0, 52.0), (1, 108.0)],
    }
    lane_to_shift = {0: 0, 1: 0}
    mapping = assign_matched_bands(
        lane_to_band_positions=lane_to_band_positions,
        lane_to_shift=lane_to_shift,
        tolerance_px=8.0,
    )

    mb00, _ = mapping[(0, 0)]
    mb10, _ = mapping[(1, 0)]
    mb01, _ = mapping[(0, 1)]
    mb11, _ = mapping[(1, 1)]

    assert mb00 == mb10
    assert mb01 == mb11
    assert mb00 != mb01

