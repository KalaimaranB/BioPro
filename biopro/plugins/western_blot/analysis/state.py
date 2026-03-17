"""Analysis pipeline state container.

``AnalysisState`` is a plain dataclass that holds every intermediate
result produced by an analysis pipeline run.  It is intentionally kept
separate from the analyzer classes so that:

- Multiple analyzer types (WesternBlot, Ponceau, SDS-PAGE, …) can each
  own their own state instance without any cross-dependency.
- UI code, dialogs, and tests can import the type without pulling in the
  full analyzer.
- The shape of the data contract is visible in one place.

Nothing in this module performs computation — it is a data container only.

Image layer model
-----------------
Three image fields form a deliberate pipeline:

``raw_image``
    Pixels loaded directly from disk.  Never modified after load.
    Source of truth for all re-processing.

``base_image``
    ``raw_image`` after inversion, contrast adjustment, and rotation —
    but **before** any crop.  This is the stable coordinate space: crop
    rectangles are always expressed in ``base_image`` pixel coordinates.
    Recomputed whenever inversion/contrast/rotation changes.

``processed_image``  (= analysis image)
    ``base_image`` after the crop rectangle is applied.  This is what
    lane detection and band detection actually operate on.  When no crop
    is active, ``processed_image is base_image``.

``detection_image``
    Set only when optional CLAHE/denoising enhancement is applied inside
    ``detect_bands``.  Band detection uses this instead of
    ``processed_image`` so that profile-based operations (flip, manual
    add) always see the same pixels as the initial detection pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from biopro.plugins.western_blot.analysis.lane_detection import LaneROI
from biopro.plugins.western_blot.analysis.peak_analysis import DetectedBand


@dataclass
class AnalysisState:
    """Mutable state for a single analysis run.

    Each field maps to one pipeline stage.  Fields are reset by the
    analyzer whenever an upstream step is re-run, so the state is always
    internally consistent.

    Attributes:
        image_path:       Path to the source image file on disk.
        raw_image:        Raw loaded image — never modified after load.
                          Alias ``original_image`` is preserved for
                          back-compatibility.
        base_image:       Image after inversion, rotation, and contrast —
                          but before crop.  Crop rects are always in
                          these pixel coordinates.
        processed_image:  Image after crop applied to ``base_image``.
                          This is what lane/band detection operates on.
                          Equal to ``base_image`` when no crop is active.
        detection_image:  Image actually used for band detection profiles
                          (may differ from ``processed_image`` if optional
                          CLAHE enhancement was applied).
        is_inverted:      Whether LUT inversion was applied.
        rotation_angle:   Rotation applied in degrees (positive = CCW).
        contrast_alpha:   Contrast multiplier (output = α·pixel + β).
        contrast_beta:    Brightness offset.
        manual_crop_rect: Active crop as (x, y, width, height) in
                          ``base_image`` pixel coordinates, or None.
        lanes:            Detected lane boundaries, ordered left-to-right.
        profiles:         Per-lane 1-D intensity profiles.
        baselines:        Per-lane estimated background baselines.
        lane_orientations: Per-lane flag — True when bands were originally
                           valleys and were flipped to peaks.
        bands:            All detected bands across all lanes.
        results_df:       Final densitometry DataFrame, or None.
    """

    # ── Image layers ──────────────────────────────────────────────────
    image_path: Optional[Path] = None

    # Raw pixels from disk — never touched after load
    raw_image: Optional[NDArray[np.float64]] = None

    # Post inversion+contrast+rotation, pre-crop — stable coord space
    base_image: Optional[NDArray[np.float64]] = None

    # Post crop (= base_image when no crop) — used by analysis pipeline
    processed_image: Optional[NDArray[np.float64]] = None

    # Optional enhanced image used by detect_bands
    detection_image: Optional[NDArray[np.float64]] = None

    # ── Back-compat alias ─────────────────────────────────────────────
    # Code that references state.original_image still works.
    @property
    def original_image(self) -> Optional[NDArray[np.float64]]:
        return self.raw_image

    @original_image.setter
    def original_image(self, value: Optional[NDArray[np.float64]]) -> None:
        self.raw_image = value

    # ── Preprocessing parameters ──────────────────────────────────────
    is_inverted: bool = False
    rotation_angle: float = 0.0
    contrast_alpha: float = 1.0
    contrast_beta: float = 0.0

    # Crop rect in base_image coordinates
    manual_crop_rect: Optional[tuple[int, int, int, int]] = None

    # ── Lane detection ─────────────────────────────────────────────────
    lanes: list[LaneROI] = field(default_factory=list)

    # ── Band detection ─────────────────────────────────────────────────
    profiles: list[NDArray[np.float64]] = field(default_factory=list)
    baselines: list[NDArray[np.float64]] = field(default_factory=list)
    lane_orientations: list[bool] = field(default_factory=list)
    bands: list[DetectedBand] = field(default_factory=list)

    # ── Densitometry ──────────────────────────────────────────────────
    results_df: Optional[pd.DataFrame] = None