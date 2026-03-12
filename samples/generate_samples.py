"""Synthetic western blot image generator for testing.

Generates realistic-looking synthetic western blot images with
configurable parameters. Useful for:
    - Unit and integration testing without real lab data.
    - Demonstrations and tutorials.
    - Validating analysis algorithms with known ground-truth values.

The generated images simulate:
    - Multiple lanes with varying band intensities.
    - Gaussian-shaped bands at configurable positions.
    - Realistic background noise and gradients.
    - Optional lane-to-lane variations (tilt, spacing).

Usage::

    python -m samples.generate_samples

Or programmatically::

    from samples.generate_samples import generate_western_blot
    image, metadata = generate_western_blot(num_lanes=6)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
from numpy.typing import NDArray


def gaussian_2d(
    shape: tuple[int, int],
    center: tuple[float, float],
    sigma_y: float,
    sigma_x: float,
    amplitude: float = 1.0,
) -> NDArray[np.float64]:
    """Generate a 2D Gaussian blob.

    Args:
        shape: (height, width) of the output array.
        center: (row, col) center of the Gaussian.
        sigma_y: Standard deviation in the vertical direction.
        sigma_x: Standard deviation in the horizontal direction.
        amplitude: Peak amplitude of the Gaussian.

    Returns:
        2D array with the Gaussian blob.
    """
    y = np.arange(shape[0])
    x = np.arange(shape[1])
    yy, xx = np.meshgrid(y, x, indexing="ij")

    exponent = -(
        ((yy - center[0]) ** 2) / (2 * sigma_y**2)
        + ((xx - center[1]) ** 2) / (2 * sigma_x**2)
    )
    return amplitude * np.exp(exponent)


def generate_western_blot(
    num_lanes: int = 6,
    num_bands: int = 3,
    image_height: int = 400,
    image_width: int = 600,
    band_intensities: Optional[list[list[float]]] = None,
    band_positions: Optional[list[float]] = None,
    noise_level: float = 0.03,
    background_gradient: float = 0.05,
    seed: Optional[int] = 42,
) -> tuple[NDArray[np.float64], dict]:
    """Generate a synthetic western blot image.

    Creates a dark-bands-on-light-background image mimicking a
    typical western blot photograph.

    Args:
        num_lanes: Number of sample lanes.
        num_bands: Number of bands per lane.
        image_height: Height of the output image in pixels.
        image_width: Width of the output image in pixels.
        band_intensities: List of lists, shape (num_lanes, num_bands).
            Each value is the relative intensity [0, 1] of a band.
            If None, random intensities are generated.
        band_positions: Vertical positions of bands as fractions [0, 1]
            of the image height. If None, evenly spaced.
        noise_level: Standard deviation of Gaussian noise added.
        background_gradient: Intensity of the vertical background gradient.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (image, metadata).
        - image: float64 array in [0, 1], dark bands on light background.
        - metadata: dict with ground-truth band positions and intensities.
    """
    rng = np.random.default_rng(seed)

    # Start with a light background (white = 1.0)
    image = np.ones((image_height, image_width), dtype=np.float64)

    # Add subtle vertical gradient (slightly darker at top/bottom)
    gradient = np.linspace(0, background_gradient, image_height)
    gradient = gradient[:, np.newaxis] * np.ones(image_width)
    image -= gradient

    # Lane spacing
    lane_margin = image_width * 0.05
    lane_spacing = (image_width - 2 * lane_margin) / num_lanes
    lane_centers = [
        lane_margin + (i + 0.5) * lane_spacing for i in range(num_lanes)
    ]

    # Band positions (vertical)
    if band_positions is None:
        band_margin = 0.15  # fraction from top/bottom edge
        band_positions = np.linspace(
            band_margin, 1 - band_margin, num_bands
        ).tolist()

    band_y_positions = [int(p * image_height) for p in band_positions]

    # Band intensities (how dark each band is)
    if band_intensities is None:
        # Generate varying intensities: control lane strong, others varying
        band_intensities = []
        for i in range(num_lanes):
            lane_bands = []
            for j in range(num_bands):
                if i == 0:
                    # Control lane — strong bands
                    intensity = 0.6 + rng.uniform(-0.05, 0.05)
                else:
                    # Other lanes — varying from 0.2 to 0.8
                    intensity = rng.uniform(0.2, 0.8)
                lane_bands.append(round(float(intensity), 3))
            band_intensities.append(lane_bands)

    # Draw bands
    sigma_x = lane_spacing * 0.15   # Band width
    sigma_y = image_height * 0.025  # Band thickness

    metadata_bands = []

    for lane_idx, lane_x in enumerate(lane_centers):
        for band_idx in range(min(num_bands, len(band_positions))):
            if lane_idx >= len(band_intensities):
                break
            if band_idx >= len(band_intensities[lane_idx]):
                break

            intensity = band_intensities[lane_idx][band_idx]
            band_y = band_y_positions[band_idx]

            # Add slight random offset for realism
            y_offset = rng.integers(-3, 4)
            x_offset = rng.integers(-2, 3)

            blob = gaussian_2d(
                shape=(image_height, image_width),
                center=(band_y + y_offset, lane_x + x_offset),
                sigma_y=sigma_y * (1 + rng.uniform(-0.2, 0.2)),
                sigma_x=sigma_x * (1 + rng.uniform(-0.1, 0.1)),
                amplitude=intensity,
            )

            # Subtract from image (dark bands on light background)
            image -= blob

            metadata_bands.append({
                "lane": lane_idx,
                "band": band_idx,
                "center_y": int(band_y + y_offset),
                "center_x": int(lane_x + x_offset),
                "intensity": intensity,
            })

    # Add noise
    noise = rng.normal(0, noise_level, image.shape)
    image += noise

    # Clip to valid range
    image = np.clip(image, 0, 1)

    # Metadata
    metadata = {
        "num_lanes": num_lanes,
        "num_bands": num_bands,
        "image_size": [image_height, image_width],
        "lane_centers": [int(x) for x in lane_centers],
        "band_y_positions": band_y_positions,
        "band_intensities": band_intensities,
        "bands": metadata_bands,
        "noise_level": noise_level,
    }

    return image, metadata


def generate_inverted_blot(
    **kwargs,
) -> tuple[NDArray[np.float64], dict]:
    """Generate a synthetic western blot with inverted LUT.

    Light bands on dark background (like a chemiluminescence capture).
    Useful for testing auto-inversion detection.

    Args:
        **kwargs: Passed to ``generate_western_blot``.

    Returns:
        Same as ``generate_western_blot``, but image is inverted.
    """
    image, metadata = generate_western_blot(**kwargs)
    metadata["inverted"] = True
    return 1.0 - image, metadata


def save_sample_images(output_dir: str | Path = "samples") -> None:
    """Generate and save a set of sample western blot images.

    Creates several test images with different characteristics:
    1. Standard 6-lane blot (dark on light).
    2. Inverted 6-lane blot (light on dark).
    3. Sparse 4-lane blot with fewer bands.
    4. Dense 8-lane blot with many bands.

    Args:
        output_dir: Directory to save images and metadata.
    """
    from skimage.io import imsave

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = {
        "standard_6lane": {
            "num_lanes": 6, "num_bands": 3, "seed": 42,
        },
        "inverted_6lane": {
            "num_lanes": 6, "num_bands": 3, "seed": 42,
            "_inverted": True,
        },
        "sparse_4lane": {
            "num_lanes": 4, "num_bands": 2, "seed": 123,
            "image_width": 400,
        },
        "dense_8lane": {
            "num_lanes": 8, "num_bands": 4, "seed": 456,
            "image_width": 800,
        },
    }

    for name, params in samples.items():
        is_inverted = params.pop("_inverted", False)

        if is_inverted:
            image, metadata = generate_inverted_blot(**params)
        else:
            image, metadata = generate_western_blot(**params)

        # Save as PNG
        img_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        img_path = output_dir / f"{name}.png"
        imsave(str(img_path), img_uint8)

        # Save metadata
        meta_path = output_dir / f"{name}_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✅  Generated: {img_path}")

    print(f"\n📁  All samples saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    save_sample_images()
