"""Lane detection algorithms for gel and blot images.

This module provides algorithms to identify individual lanes in gel
electrophoresis and western blot images. Lanes are the vertical
columns where samples are loaded and separated.

The primary approach uses **vertical intensity projection** — computing
the mean intensity of each column to produce a 1-D profile. Lanes
appear as regions of lower intensity (darker bands), separated by
gaps of higher intensity (brighter background).

Design Notes:
    - All algorithms accept and return NumPy arrays.
    - Lane boundaries are represented as a list of ``(x_start, x_end)``
      tuples, where x values are column indices.
    - The module is analysis-type agnostic — it works for western blots,
      SDS-PAGE gels, and any similar banded image.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks


@dataclass
class LaneROI:
    """Region of interest representing a single lane.

    Attributes:
        index: Zero-based lane number (left-to-right).
        x_start: Left column boundary (inclusive).
        x_end: Right column boundary (exclusive).
        y_start: Top row boundary (inclusive).
        y_end: Bottom row boundary (exclusive).
        center_x: Horizontal center of the lane.
    """

    index: int
    x_start: int
    x_end: int
    y_start: int
    y_end: int

    @property
    def center_x(self) -> int:
        """Horizontal center column of the lane."""
        return (self.x_start + self.x_end) // 2

    @property
    def width(self) -> int:
        """Width of the lane in pixels."""
        return self.x_end - self.x_start

    @property
    def height(self) -> int:
        """Height of the lane in pixels."""
        return self.y_end - self.y_start

    def extract(self, image: NDArray[np.float64]) -> NDArray[np.float64]:
        """Extract the lane region from an image.

        Args:
            image: Source image array.

        Returns:
            Cropped image region for this lane.
        """
        return image[self.y_start : self.y_end, self.x_start : self.x_end]


def compute_vertical_projection(image: NDArray[np.float64]) -> NDArray[np.float64]:
    """Compute the vertical intensity projection of an image.

    The vertical projection is the mean intensity of each column,
    producing a 1-D signal of length equal to the image width.

    For a dark-on-light image (standard western blot), lanes will
    appear as dips (lower values) in the projection.

    Args:
        image: Grayscale float64 image.

    Returns:
        1-D array of mean column intensities, same length as image width.
    """
    return np.mean(image, axis=0)


def detect_lanes_projection(
    image: NDArray[np.float64],
    num_lanes: Optional[int] = None,
    smoothing_window: int = 15,
    min_lane_gap_fraction: float = 0.02,
) -> list[LaneROI]:
    """Detect lane boundaries using vertical intensity projection.

    Algorithm:
        1. Compute mean intensity per column (vertical projection).
        2. Smooth the projection to reduce noise.
        3. Find peaks in the projection (peaks = inter-lane gaps).
        4. Use peak positions to define lane boundaries.

    If ``num_lanes`` is specified, the algorithm selects the N most
    prominent inter-lane gaps. If not specified, it auto-detects based
    on peak prominence.

    Args:
        image: Grayscale float64 image in [0.0, 1.0].
            Should be preprocessed (inverted so that bands are dark
            on light background).
        num_lanes: Expected number of lanes. If None, auto-detect.
        smoothing_window: Width of the smoothing kernel (in pixels)
            applied to the projection profile. Larger values reduce
            noise but may merge narrow lanes.
        min_lane_gap_fraction: Minimum gap between lanes, expressed as
            a fraction of the image width. Gaps smaller than this are
            ignored.

    Returns:
        List of ``LaneROI`` objects, ordered left-to-right.

    Raises:
        ValueError: If no lanes could be detected.
    """
    h, w = image.shape[:2]

    # Step 1: Compute vertical projection
    projection = compute_vertical_projection(image)

    # Step 2: Smooth to reduce noise
    smoothed = uniform_filter1d(projection, size=smoothing_window)

    # Step 3: Find peaks (bright gaps between lanes)
    min_distance = max(3, int(w * min_lane_gap_fraction))

    # For a dark-on-light image, lane gaps are peaks (bright areas)
    peaks, properties = find_peaks(
        smoothed,
        distance=min_distance,
        prominence=0.01,
    )

    if len(peaks) == 0:
        # No gaps found — treat the entire image as one lane,
        # or fall back to equal spacing if num_lanes given.
        if num_lanes is not None:
            return create_equal_lanes(image.shape, num_lanes)
        return [LaneROI(index=0, x_start=0, x_end=w, y_start=0, y_end=h)]

    # Step 4: Select the right number of gaps
    if num_lanes is not None:
        # We need (num_lanes - 1) inter-lane gaps
        num_gaps = num_lanes - 1
        if len(peaks) >= num_gaps:
            # Select the most prominent gaps
            prominences = properties["prominences"]
            top_indices = np.argsort(prominences)[-num_gaps:]
            peaks = np.sort(peaks[top_indices])
        else:
            # Not enough gaps detected — use what we have
            pass

    # Step 5: Build lane boundaries from gap positions
    boundaries: list[int] = [0]
    for peak in peaks:
        boundaries.append(int(peak))
    boundaries.append(w)

    # Create LaneROI objects
    lanes = []
    for i in range(len(boundaries) - 1):
        lanes.append(
            LaneROI(
                index=i,
                x_start=boundaries[i],
                x_end=boundaries[i + 1],
                y_start=0,
                y_end=h,
            )
        )

    return lanes


def create_equal_lanes(
    image_shape: tuple[int, ...],
    num_lanes: int,
    margin_fraction: float = 0.02,
) -> list[LaneROI]:
    """Create equally-spaced lane ROIs.

    Used as a fallback when auto-detection fails, or when the user
    specifies the lane count and wants uniform spacing.

    Args:
        image_shape: Shape of the image ``(height, width, ...)``.
        num_lanes: Number of lanes to create.
        margin_fraction: Fraction of width to leave as margin on each side.

    Returns:
        List of ``LaneROI`` objects with equal widths.

    Raises:
        ValueError: If num_lanes < 1.
    """
    if num_lanes < 1:
        raise ValueError(f"num_lanes must be >= 1, got {num_lanes}")

    h, w = image_shape[:2]
    margin = int(w * margin_fraction)
    usable_width = w - 2 * margin
    lane_width = usable_width // num_lanes

    lanes = []
    for i in range(num_lanes):
        x_start = margin + i * lane_width
        x_end = margin + (i + 1) * lane_width if i < num_lanes - 1 else w - margin
        lanes.append(
            LaneROI(
                index=i,
                x_start=x_start,
                x_end=x_end,
                y_start=0,
                y_end=h,
            )
        )

    return lanes
