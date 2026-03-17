"""Tests for lane detection algorithms."""

from __future__ import annotations

import numpy as np
import pytest

from biopro.plugins.western_blot.analysis.lane_detection import (
    LaneROI,
    compute_vertical_projection,
    create_equal_lanes,
    detect_lanes_projection,
)


class TestLaneROI:
    """Tests for the LaneROI dataclass."""

    def test_properties(self) -> None:
        """Properties should compute correctly."""
        roi = LaneROI(index=0, x_start=10, x_end=50, y_start=0, y_end=100)
        assert roi.center_x == 30
        assert roi.width == 40
        assert roi.height == 100

    def test_extract(self) -> None:
        """Extract should return the correct sub-image."""
        image = np.arange(200).reshape(10, 20).astype(np.float64)
        roi = LaneROI(index=0, x_start=5, x_end=10, y_start=2, y_end=8)
        extracted = roi.extract(image)
        assert extracted.shape == (6, 5)


class TestVerticalProjection:
    """Tests for compute_vertical_projection."""

    def test_uniform_image(self) -> None:
        """Uniform image should have constant projection."""
        image = np.ones((50, 100), dtype=np.float64) * 0.5
        proj = compute_vertical_projection(image)
        assert len(proj) == 100
        np.testing.assert_array_almost_equal(proj, 0.5)

    def test_bright_column(self) -> None:
        """A bright column should show a peak in the projection."""
        image = np.ones((50, 100), dtype=np.float64) * 0.2
        image[:, 50] = 1.0
        proj = compute_vertical_projection(image)
        assert proj[50] > proj[0]


class TestDetectLanesProjection:
    """Tests for auto lane detection."""

    def test_clear_lanes(self) -> None:
        """Synthetic image with clear lanes should be detected correctly."""
        # Create a synthetic image with 4 clear lanes
        image = np.ones((200, 400), dtype=np.float64) * 0.9  # Light background

        # Add 4 dark lanes
        lane_width = 80
        gap = 20
        for i in range(4):
            x_start = gap + i * (lane_width + gap)
            x_end = x_start + lane_width
            image[:, x_start:x_end] = 0.3  # Dark lanes

        lanes = detect_lanes_projection(image, num_lanes=4)
        assert len(lanes) == 4

        # Verify they're ordered left-to-right
        for i in range(len(lanes) - 1):
            assert lanes[i].x_start < lanes[i + 1].x_start

    def test_specified_lane_count(self) -> None:
        """Specifying num_lanes should return that many lanes."""
        image = np.ones((100, 300), dtype=np.float64) * 0.8
        # Simple image with some structure
        for i in range(5):
            x = 30 + i * 50
            image[:, x : x + 30] = 0.3

        lanes = detect_lanes_projection(image, num_lanes=5)
        assert len(lanes) == 5

    def test_single_lane_fallback(self) -> None:
        """Uniform image should fall back to single lane or equal spacing."""
        image = np.ones((100, 200), dtype=np.float64) * 0.5
        lanes = detect_lanes_projection(image)
        assert len(lanes) >= 1


class TestCreateEqualLanes:
    """Tests for create_equal_lanes."""

    def test_correct_count(self) -> None:
        """Should create the requested number of lanes."""
        lanes = create_equal_lanes((100, 400), num_lanes=6)
        assert len(lanes) == 6

    def test_lanes_cover_image(self) -> None:
        """Lanes should approximately cover the image width."""
        lanes = create_equal_lanes((100, 400), num_lanes=4, margin_fraction=0.0)
        total_width = sum(l.width for l in lanes)
        assert total_width == 400

    def test_invalid_count_raises(self) -> None:
        """num_lanes < 1 should raise ValueError."""
        with pytest.raises(ValueError):
            create_equal_lanes((100, 400), num_lanes=0)
