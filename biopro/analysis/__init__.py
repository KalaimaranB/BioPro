"""Analysis sub-package — headless image processing engine.

This package contains all image analysis algorithms and pipelines.
It is fully independent of the UI layer, so it can be used in scripts,
Jupyter notebooks, or integrated into other tools.

Modules:
    image_utils: Image loading, format conversion, and preprocessing utilities.
    lane_detection: Algorithms for detecting lane boundaries in gel/blot images.
    peak_analysis: Peak detection, baseline estimation, and densitometry.
    western_blot: High-level ``WesternBlotAnalyzer`` pipeline that orchestrates
        all analysis steps.

Quick Start::

    from biopro.analysis import WesternBlotAnalyzer

    analyzer = WesternBlotAnalyzer()
    analyzer.load_image("my_blot.tif")
    analyzer.preprocess()
    analyzer.detect_lanes()
    analyzer.detect_bands()
    analyzer.compute_densitometry()
    results = analyzer.get_results()
"""

from biopro.analysis.western_blot import WesternBlotAnalyzer

__all__ = ["WesternBlotAnalyzer"]
