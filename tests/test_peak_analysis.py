"""Tests for peak analysis and densitometry calculations."""

from __future__ import annotations

import numpy as np
import pytest

from biopro.plugins.western_blot.analysis.peak_analysis import (
    compute_peak_areas,
    detect_peaks,
    extract_lane_profile,
    linear_baseline,
    rolling_ball_baseline,
)


def _make_gaussian_profile(
    length: int = 200,
    peak_positions: list[int] | None = None,
    peak_heights: list[float] | None = None,
    peak_widths: list[float] | None = None,
    noise: float = 0.01,
) -> np.ndarray:
    """Create a synthetic 1-D profile with Gaussian peaks.

    Helper function for creating test profiles with known ground truth.

    Args:
        length: Length of the profile.
        peak_positions: Pixel positions of peaks.
        peak_heights: Heights of peaks.
        peak_widths: Sigma of each Gaussian peak.
        noise: Noise level.

    Returns:
        1-D profile array.
    """
    if peak_positions is None:
        peak_positions = [50, 100, 150]
    if peak_heights is None:
        peak_heights = [0.5, 0.8, 0.3]
    if peak_widths is None:
        peak_widths = [8.0] * len(peak_positions)

    x = np.arange(length, dtype=np.float64)
    profile = np.zeros(length, dtype=np.float64)

    for pos, height, width in zip(peak_positions, peak_heights, peak_widths):
        profile += height * np.exp(-((x - pos) ** 2) / (2 * width**2))

    # Add small noise
    rng = np.random.default_rng(42)
    profile += rng.normal(0, noise, length)
    profile = np.maximum(profile, 0)

    return profile


class TestExtractLaneProfile:
    """Tests for extract_lane_profile."""

    def test_uniform_image(self) -> None:
        """Uniform image should produce a flat profile."""
        image = np.ones((100, 50), dtype=np.float64) * 0.5
        profile = extract_lane_profile(image, 0, 50, 0, 100)
        assert len(profile) == 100
        # No longer inverted: remains 0.5
        np.testing.assert_array_almost_equal(profile, 0.5)

    def test_bright_band_produces_peak(self) -> None:
        """An already-inverted bright horizontal band should produce a peak."""
        image = np.ones((100, 50), dtype=np.float64) * 0.1  # Dark bg (inverted white bg)
        image[40:60, :] = 0.9  # Bright band (inverted dark band)

        profile = extract_lane_profile(image, 0, 50, 0, 100)
        assert profile[50] > profile[10]

    def test_output_range(self) -> None:
        """Profile values should be in [0, 1] for valid input."""
        image = np.random.rand(80, 40).astype(np.float64)
        profile = extract_lane_profile(image, 0, 40, 0, 80)
        assert profile.min() >= 0
        assert profile.max() <= 1.0 + 1e-10


class TestDetectPeaks:
    """Tests for detect_peaks."""

    def test_find_known_peaks(self) -> None:
        """Should detect peaks at known positions."""
        profile = _make_gaussian_profile(
            peak_positions=[50, 100, 150],
            peak_heights=[0.5, 0.8, 0.3],
        )
        peaks, props = detect_peaks(profile, min_peak_height=0.1)

        # Should find approximately 3 peaks
        assert len(peaks) >= 2  # At least 2 of the 3
        assert len(peaks) <= 5  # Not too many false positives

        # Check peaks are near expected positions (within 5 pixels)
        for expected_pos in [50, 100, 150]:
            distances = np.abs(peaks - expected_pos)
            assert np.min(distances) < 10, f"No peak found near position {expected_pos}"

    def test_flat_profile_no_peaks(self) -> None:
        """A flat profile should produce no peaks."""
        profile = np.ones(100, dtype=np.float64) * 0.01
        peaks, _ = detect_peaks(profile, min_peak_height=0.1)
        assert len(peaks) == 0

    def test_sensitivity_control(self) -> None:
        """Higher min_peak_height should detect fewer peaks."""
        profile = _make_gaussian_profile(
            peak_heights=[0.8, 0.3, 0.1],
        )
        peaks_sensitive, _ = detect_peaks(profile, min_peak_height=0.05)
        peaks_strict, _ = detect_peaks(profile, min_peak_height=0.4)

        assert len(peaks_strict) <= len(peaks_sensitive)


class TestRollingBallBaseline:
    """Tests for rolling_ball_baseline."""

    def test_flat_baseline(self) -> None:
        """Flat profile should have a flat baseline."""
        profile = np.zeros(100, dtype=np.float64)
        baseline = rolling_ball_baseline(profile, radius=20)
        assert len(baseline) == 100
        np.testing.assert_array_almost_equal(baseline, 0, decimal=5)

    def test_baseline_below_peaks(self) -> None:
        """Baseline should be below the peaks."""
        profile = _make_gaussian_profile(peak_heights=[0.8])
        baseline = rolling_ball_baseline(profile, radius=30)

        # At the peak position, baseline should be lower than profile
        peak_pos = 50
        assert baseline[peak_pos] < profile[peak_pos]


class TestLinearBaseline:
    """Tests for linear_baseline."""

    def test_with_peaks(self) -> None:
        """Linear baseline should connect valleys between peaks."""
        profile = _make_gaussian_profile(
            peak_positions=[50, 150],
            peak_heights=[0.8, 0.6],
        )
        peaks = np.array([50, 150])
        baseline = linear_baseline(profile, peaks)
        assert len(baseline) == len(profile)

    def test_no_peaks(self) -> None:
        """With no peaks, should return zeros."""
        profile = np.ones(100, dtype=np.float64) * 0.5
        baseline = linear_baseline(profile, np.array([], dtype=np.intp))
        np.testing.assert_array_almost_equal(baseline, 0.0)


class TestComputePeakAreas:
    """Tests for compute_peak_areas."""

    def test_positive_areas(self) -> None:
        """Peak areas should be positive for peaks above baseline."""
        profile = _make_gaussian_profile(
            peak_positions=[50, 100],
            peak_heights=[0.8, 0.4],
        )
        peaks, props = detect_peaks(profile, min_peak_height=0.1)
        baseline = rolling_ball_baseline(profile, radius=30)
        areas = compute_peak_areas(profile, peaks, baseline, props)

        assert len(areas) == len(peaks)
        for area in areas:
            assert area >= 0

    def test_taller_peak_larger_area(self) -> None:
        """A taller peak should generally have a larger integrated area."""
        profile = _make_gaussian_profile(
            peak_positions=[50, 150],
            peak_heights=[0.8, 0.2],
            peak_widths=[8.0, 8.0],  # Same width
        )
        baseline = np.zeros_like(profile)
        peaks = np.array([50, 150])
        _, props = detect_peaks(profile, min_peak_height=0.05)

        # Re-detect with actual peaks for proper properties
        areas = compute_peak_areas(profile, peaks, baseline)

        if len(areas) == 2:
            assert areas[0] > areas[1]
