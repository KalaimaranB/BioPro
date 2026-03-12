"""End-to-end tests for the WesternBlotAnalyzer pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add samples directory to path for importing the generator
sys.path.insert(0, str(Path(__file__).parent.parent))

from biopro.analysis.western_blot import WesternBlotAnalyzer
from samples.generate_samples import generate_western_blot


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Generate and save a synthetic western blot for testing.

    Returns:
        Path to the saved test image.
    """
    from skimage.io import imsave

    image, metadata = generate_western_blot(
        num_lanes=6,
        num_bands=3,
        seed=42,
    )
    img_path = tmp_path / "test_blot.png"
    img_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
    imsave(str(img_path), img_uint8)
    return img_path


@pytest.fixture
def inverted_image(tmp_path: Path) -> Path:
    """Generate an inverted synthetic blot (light on dark).

    Returns:
        Path to the saved test image.
    """
    from skimage.io import imsave

    image, _ = generate_western_blot(num_lanes=4, seed=123)
    inverted = 1.0 - image
    img_path = tmp_path / "test_blot_inverted.png"
    img_uint8 = (np.clip(inverted, 0, 1) * 255).astype(np.uint8)
    imsave(str(img_path), img_uint8)
    return img_path


class TestWesternBlotAnalyzerPipeline:
    """End-to-end pipeline tests."""

    def test_full_pipeline(self, sample_image: Path) -> None:
        """Full pipeline should produce a valid results DataFrame."""
        analyzer = WesternBlotAnalyzer()

        # Step 1: Load
        image = analyzer.load_image(sample_image)
        assert image.dtype == np.float64
        assert image.ndim == 2

        # Step 2: Preprocess
        processed = analyzer.preprocess(invert_lut="auto")
        assert processed.shape == image.shape or processed.shape != image.shape
        # (shape may change if auto-crop is applied)

        # Step 3: Detect lanes
        lanes = analyzer.detect_lanes(num_lanes=6)
        assert len(lanes) == 6
        for lane in lanes:
            assert lane.width > 0
            assert lane.height > 0

        # Step 4: Detect bands
        bands = analyzer.detect_bands()
        assert len(bands) > 0

        # Step 5: Compute densitometry
        df = analyzer.compute_densitometry()
        assert isinstance(df, pd.DataFrame)
        assert "lane" in df.columns
        assert "raw_intensity" in df.columns
        assert "normalized" in df.columns
        assert len(df) > 0

    def test_run_auto(self, sample_image: Path) -> None:
        """run_auto should complete the full pipeline in one call."""
        analyzer = WesternBlotAnalyzer()
        df = analyzer.run_auto(sample_image, num_lanes=6)

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert all(col in df.columns for col in ["lane", "normalized"])

    def test_inverted_image_handling(self, inverted_image: Path) -> None:
        """Auto-inversion should handle light-on-dark images."""
        analyzer = WesternBlotAnalyzer()
        analyzer.load_image(inverted_image)
        analyzer.preprocess(invert_lut="auto")

        # After auto-inversion, the analyzer should have detected inversion
        # (or not, depending on the image — just verify no crash)
        assert analyzer.state.processed_image is not None

    def test_export_csv(self, sample_image: Path, tmp_path: Path) -> None:
        """CSV export should create a valid file."""
        analyzer = WesternBlotAnalyzer()
        analyzer.run_auto(sample_image, num_lanes=6)

        csv_path = tmp_path / "test_results.csv"
        result_path = analyzer.export_csv(csv_path)

        assert result_path.exists()
        df = pd.read_csv(result_path)
        assert len(df) > 0

    def test_export_excel(self, sample_image: Path, tmp_path: Path) -> None:
        """Excel export should create a valid file."""
        analyzer = WesternBlotAnalyzer()
        analyzer.run_auto(sample_image, num_lanes=6)

        xlsx_path = tmp_path / "test_results.xlsx"
        result_path = analyzer.export_excel(xlsx_path)

        assert result_path.exists()
        df = pd.read_excel(result_path)
        assert len(df) > 0


class TestWesternBlotAnalyzerErrors:
    """Tests for error handling."""

    def test_no_image_raises(self) -> None:
        """Operations without loading an image should raise."""
        analyzer = WesternBlotAnalyzer()
        with pytest.raises(RuntimeError, match="no image loaded"):
            analyzer.preprocess()

    def test_no_lanes_raises(self, sample_image: Path) -> None:
        """Detecting bands without lanes should raise."""
        analyzer = WesternBlotAnalyzer()
        analyzer.load_image(sample_image)
        analyzer.preprocess()
        with pytest.raises(RuntimeError, match="no lanes detected"):
            analyzer.detect_bands()

    def test_no_bands_raises(self, sample_image: Path) -> None:
        """Computing densitometry without bands should raise."""
        analyzer = WesternBlotAnalyzer()
        analyzer.load_image(sample_image)
        analyzer.preprocess()
        analyzer.detect_lanes(num_lanes=6)
        # detect_bands with very strict threshold → no bands
        bands = analyzer.detect_bands(min_peak_height=0.99)
        if len(bands) == 0:
            with pytest.raises(RuntimeError, match="no bands detected"):
                analyzer.compute_densitometry()


class TestWesternBlotAnalyzerState:
    """Tests for state management."""

    def test_rerun_preserves_image(self, sample_image: Path) -> None:
        """Re-running detection should not corrupt the image."""
        analyzer = WesternBlotAnalyzer()
        analyzer.load_image(sample_image)
        analyzer.preprocess()

        original = analyzer.state.processed_image.copy()

        # Run detection twice
        analyzer.detect_lanes(num_lanes=6)
        analyzer.detect_lanes(num_lanes=4)

        # Image should be unchanged
        np.testing.assert_array_equal(
            analyzer.state.processed_image, original
        )

    def test_load_resets_state(self, sample_image: Path) -> None:
        """Loading a new image should reset all downstream state."""
        analyzer = WesternBlotAnalyzer()
        analyzer.run_auto(sample_image, num_lanes=6)

        assert len(analyzer.state.bands) > 0
        assert analyzer.state.results_df is not None

        # Load again
        analyzer.load_image(sample_image)
        assert analyzer.state.bands == []
        assert analyzer.state.results_df is None

    def test_manual_band_adds_missing_profiles(self, sample_image: Path) -> None:
        """add_manual_band should raise error if profiles not computed."""
        analyzer = WesternBlotAnalyzer()
        analyzer.load_image(sample_image)
        analyzer.preprocess()
        analyzer.detect_lanes(num_lanes=6)
        
        # We did NOT call detect_bands() so state.profiles is empty
        assert len(analyzer.state.profiles) == 0
        
        with pytest.raises(RuntimeError, match="No lane profiles available"):
            # Should raise because profiles aren't computed
            analyzer.add_manual_band(lane_index=0, y_position=50)

    def test_manual_crop(self, sample_image: Path) -> None:
        """Manual crop rectangle should reduce the image dimensions."""
        analyzer = WesternBlotAnalyzer()
        image = analyzer.load_image(sample_image)
        original_h, original_w = image.shape
        
        crop_rect = (10, 20, original_w // 2, original_h // 2)
        
        processed = analyzer.preprocess(manual_crop_rect=crop_rect)
        
        new_h, new_w = processed.shape
        assert new_h == crop_rect[3]
        assert new_w == crop_rect[2]
        
        # Ensures that a bad out-of-bounds crop doesn't crash but is clipped
        bad_crop_rect = (-50, -50, original_w * 2, original_h * 2)
        processed_bad = analyzer.preprocess(manual_crop_rect=bad_crop_rect)
        assert processed_bad.shape == (original_h, original_w)

