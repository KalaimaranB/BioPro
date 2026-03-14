"""Image loading, format conversion, and preprocessing utilities.

This module provides low-level image I/O and transformation functions
used throughout the BioPro analysis pipeline. All functions operate on
NumPy arrays and are agnostic to the analysis type.

Design Notes:
    - Images are represented as ``numpy.ndarray`` with dtype ``float64``
      and values in the range [0.0, 1.0].
    - Grayscale conversion uses luminance-weighted averaging.
    - All functions are pure (no side effects) and stateless.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from numpy.typing import NDArray
from skimage import io as skio
from skimage.color import rgb2gray
from skimage import exposure
from skimage.transform import rotate
from skimage.util import img_as_float64
from scipy.ndimage import gaussian_filter, median_filter


def adjust_contrast(image: NDArray[np.float64], alpha: float = 1.0, beta: float = 0.0) -> NDArray[np.float64]:
    """Adjust contrast and brightness of a float64 image.
    
    Formula: output = alpha * image + beta
    
    Args:
        image: Float64 image in [0.0, 1.0].
        alpha: Contrast control (1.0 = original, >1.0 = more contrast, <1.0 = less contrast).
        beta: Brightness control (0.0 = original, >0.0 = brighter, <0.0 = darker).
        
    Returns:
        Adjusted float64 image clipped to [0.0, 1.0].
    """
    if abs(alpha - 1.0) < 0.001 and abs(beta) < 0.001:
        return image.copy()
        
    adjusted = image * alpha + beta
    return np.clip(adjusted, 0.0, 1.0)


def load_and_convert(
    path: Union[str, Path],
    as_grayscale: bool = True,
) -> NDArray[np.float64]:
    """Load an image from disk and convert to normalized float64.

    Supports all formats handled by scikit-image (TIFF, PNG, JPG, BMP, etc.),
    including 16-bit and 32-bit scientific image formats.

    Args:
        path: Path to the image file.
        as_grayscale: If True (default), convert to single-channel grayscale.
            If False, return as RGB float64 with shape (H, W, 3).

    Returns:
        Image as a float64 array with values in [0.0, 1.0].

    Raises:
        FileNotFoundError: If the image file does not exist.
        ValueError: If the file cannot be read as an image.

    Example::

        >>> img = load_and_convert("blot.tif")
        >>> img.dtype
        dtype('float64')
        >>> 0.0 <= img.min() <= img.max() <= 1.0
        True
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    try:
        image = skio.imread(str(path))
    except Exception as exc:
        raise ValueError(f"Could not read image file '{path}': {exc}") from exc

    # Convert to float64 in [0, 1]
    image = img_as_float64(image)

    # Handle RGBA by dropping alpha channel
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]

    # Convert to grayscale if requested
    if as_grayscale and image.ndim == 3:
        image = rgb2gray(image)

    return image


def auto_detect_inversion(image: NDArray[np.float64]) -> bool:
    """Determine whether the image LUT should be inverted.

    Western blot images may have either:

    - **Light background with dark bands** (standard case) — this should
      generally *not* be inverted; the analysis pipeline can work directly
      with dark valleys against a bright background.
    - **Dark background with light bands** — in this case inversion is
      helpful so that bands become bright peaks on a light background.

    This heuristic is deliberately conservative and will only request
    inversion when the image looks like ``light bands on dark background``.

    Args:
        image: Grayscale float64 image in [0.0, 1.0].

    Returns:
        True if the image should be inverted (dark background, light bands),
        False otherwise.
    """
    h, w = image.shape[:2]

    # Ignore exact 0.0 pixels which are likely rotation padding
    valid_pixels = image[image > 0.0]
    if len(valid_pixels) == 0:
        return False

    # Primary heuristic: check overall image median
    overall_median = float(np.median(valid_pixels))

    # Predominantly light background (standard blot: white bg, dark bands)
    # → do NOT invert.
    if overall_median > 0.6:
        return False

    # Predominantly dark background → candidate for inversion if the center
    # region contains brighter structures than the corners.
    if overall_median < 0.4:
        corner_size_h = max(1, h // 10)
        corner_size_w = max(1, w // 10)

        corners = np.concatenate(
            [
                image[:corner_size_h, :corner_size_w].ravel(),  # top-left
                image[:corner_size_h, -corner_size_w:].ravel(),  # top-right
                image[-corner_size_h:, :corner_size_w].ravel(),  # bottom-left
                image[-corner_size_h:, -corner_size_w:].ravel(),  # bottom-right
            ]
        )
        corners = corners[corners > 0.0]

        ch, cw = h // 4, w // 4
        center = image[ch : h - ch, cw : w - cw].ravel()
        center = center[center > 0.0]

        if len(center) == 0 or len(corners) == 0:
            # Fall back to overall darkness: dark images default to invert.
            return True

        corner_median = float(np.median(corners))
        center_median = float(np.median(center))

        # If the center is meaningfully brighter than the corners, we likely
        # have light bands on a dark background → invert.
        return center_median > corner_median + 0.05

    # For ambiguous mid-range cases (overall ~mid-gray), compare corners to center.
    corner_size_h = max(1, h // 10)
    corner_size_w = max(1, w // 10)

    corners = np.concatenate(
        [
            image[:corner_size_h, :corner_size_w].ravel(),
            image[:corner_size_h, -corner_size_w:].ravel(),
            image[-corner_size_h:, :corner_size_w].ravel(),
            image[-corner_size_h:, -corner_size_w:].ravel(),
        ]
    )
    corners = corners[corners > 0.0]

    ch, cw = h // 4, w // 4
    center = image[ch : h - ch, cw : w - cw].ravel()
    center = center[center > 0.0]

    if len(center) == 0 or len(corners) == 0:
        return False

    corner_median = float(np.median(corners))
    center_median = float(np.median(center))

    # Ambiguous images: only invert if the center is clearly brighter than
    # the corners (again indicating light bands on darker surround).
    return center_median > corner_median + 0.05


def invert_image(image: NDArray[np.float64]) -> NDArray[np.float64]:
    """Invert a normalized float64 image (1.0 - image).

    Args:
        image: Float64 image in [0.0, 1.0].

    Returns:
        Inverted image.
    """
    return 1.0 - image


def enhance_for_band_detection(
    image: NDArray[np.float64],
    *,
    apply_clahe: bool = True,
    clahe_clip_limit: float = 2.0,
    clahe_tile_grid_size: int = 8,
    denoise_median_ksize: int = 0,
    background_kernel_size: int = 0,
) -> NDArray[np.float64]:
    """Enhance contrast and flatten background for band detection.

    This function is intended to be used *after* polarity normalization so that
    bands are peaks (higher intensity) and background is lower intensity.

    Steps (all optional):
    - CLAHE (local contrast enhancement)
    - Median denoise (speckle/dust suppression)
    - Large-kernel background estimation + subtraction (gradient flattening)

    Args:
        image: Grayscale float64 in [0, 1].
        apply_clahe: Apply CLAHE to boost local contrast.
        clahe_clip_limit: CLAHE clip limit (higher = more contrast).
        clahe_tile_grid_size: CLAHE tile grid size in pixels (OpenCV uses (n,n)).
        denoise_median_ksize: Median blur kernel size (odd int). 0 disables.
        background_kernel_size: Gaussian blur kernel size (odd int) used to
            estimate background. 0 disables.

    Returns:
        Enhanced float64 image in [0, 1].
    """
    out = np.clip(image, 0.0, 1.0)

    if apply_clahe:
        # scikit-image's equalize_adapthist is CLAHE-like
        # clip_limit is in [0, 1] for skimage; map from a more UI-friendly range.
        clip = float(np.clip(clahe_clip_limit / 10.0, 0.001, 0.2))
        # kernel_size can be an int (square) or (rows, cols)
        k = int(max(2, clahe_tile_grid_size))
        out = exposure.equalize_adapthist(out, clip_limit=clip, kernel_size=k)

    if denoise_median_ksize and denoise_median_ksize >= 3:
        k = int(denoise_median_ksize)
        if k % 2 == 0:
            k += 1
        out = median_filter(out, size=(k, k))

    if background_kernel_size and background_kernel_size >= 5:
        k = int(background_kernel_size)
        if k % 2 == 0:
            k += 1
        # Approximate OpenCV kernel-size behavior with sigma.
        # For a Gaussian kernel, sigma ~ k/6 is a common rule of thumb.
        sigma = max(1.0, float(k) / 6.0)
        bg = gaussian_filter(out, sigma=sigma)
        out = out - bg
        # Robust rescale back to [0, 1]
        lo, hi = np.percentile(out, [1.0, 99.5])
        if hi > lo:
            out = (out - lo) / (hi - lo)
        out = np.clip(out, 0.0, 1.0)

    return out


def rotate_image(
    image: NDArray[np.float64],
    angle: float,
    fill_value: float = 1.0,
) -> NDArray[np.float64]:
    """Rotate an image by the given angle in degrees.

    Positive angles rotate counter-clockwise. The image is resized to
    contain the full rotated content (no cropping).

    Args:
        image: Float64 image.
        angle: Rotation angle in degrees. Positive = counter-clockwise.
        fill_value: Value to fill border pixels created by rotation.
            Default 1.0 (white) suits dark-on-light blot images.

    Returns:
        Rotated image as float64.
    """
    if abs(angle) < 0.01:
        return image.copy()

    return rotate(
        image,
        angle=angle,
        resize=True,
        mode="constant",
        cval=fill_value,
        preserve_range=True,
    )


def crop_to_content(
    image: NDArray[np.float64],
    threshold: float = 0.95,
    padding: int = 10,
) -> NDArray[np.float64]:
    """Auto-crop whitespace/blackspace borders from an image.

    Removes rows and columns from the borders where all pixel values
    are above the threshold (considered background).

    Args:
        image: Grayscale float64 image in [0.0, 1.0].
        threshold: Pixel values above this are considered background.
            For inverted images (dark bands on light bg), use ~0.95.
        padding: Number of pixels to keep around the detected content.

    Returns:
        Cropped image.
    """
    # Find rows and columns with content (below threshold)
    content_mask = image < threshold

    # Find bounding box of content
    rows_with_content = np.any(content_mask, axis=1)
    cols_with_content = np.any(content_mask, axis=0)

    if not np.any(rows_with_content) or not np.any(cols_with_content):
        return image  # No content detected — return original

    row_indices = np.where(rows_with_content)[0]
    col_indices = np.where(cols_with_content)[0]

    r_min = max(0, row_indices[0] - padding)
    r_max = min(image.shape[0], row_indices[-1] + padding + 1)
    c_min = max(0, col_indices[0] - padding)
    c_max = min(image.shape[1], col_indices[-1] + padding + 1)

    return image[r_min:r_max, c_min:c_max]


def auto_contrast_stretch(
    image: NDArray[np.float64],
    low_pct: float = 1.0,
    high_pct: float = 99.0,
) -> tuple[float, float]:
    """Compute optimal contrast alpha/beta by percentile stretching.

    Finds the alpha (contrast) and beta (brightness offset) values that
    stretch the meaningful pixel range to fill [0, 1], ignoring the
    darkest ``low_pct``% and brightest ``high_pct``% as outliers.

    Args:
        image: Grayscale float64 image in [0.0, 1.0].
        low_pct: Lower percentile to clip (outlier dark pixels).
        high_pct: Upper percentile to clip (outlier bright pixels).

    Returns:
        Tuple of (alpha, beta) ready to pass to ``adjust_contrast``.
    """
    valid = image[image > 0.0] if np.any(image > 0.0) else image.ravel()
    p_lo = float(np.percentile(valid, low_pct))
    p_hi = float(np.percentile(valid, high_pct))

    if p_hi <= p_lo:
        return 1.0, 0.0

    alpha = round(1.0 / (p_hi - p_lo), 3)
    beta = round(-p_lo * alpha, 3)
    alpha = float(np.clip(alpha, 0.1, 5.0))
    beta = float(np.clip(beta, -1.0, 1.0))
    return alpha, beta


def auto_detect_rotation(
    image: NDArray[np.float64],
    angle_range: float = 15.0,
    angle_step: float = 0.25,
) -> float:
    """Detect the tilt angle of horizontal bands in a western blot image.

    Strategy:
        1. Contrast-stretch so bands are visible.
        2. Compute horizontal Sobel edges — band edges are strong
           horizontal features.
        3. Sweep candidate angles; pick the one that maximises the
           variance of the vertical projection of the edge image.
           When bands are perfectly horizontal each band collapses to
           a sharp spike in the projection → variance is maximised.

    Args:
        image: Grayscale float64 image in [0.0, 1.0].
        angle_range: Search ±angle_range degrees from zero.
        angle_step: Angular resolution in degrees.

    Returns:
        Estimated correction angle in degrees (positive = counter-clockwise).
        Returns 0.0 if no clear tilt is found.
    """
    from scipy.ndimage import sobel
    from skimage.transform import rotate as sk_rotate

    # Downsample for speed
    h, w = image.shape[:2]
    scale = min(1.0, 400.0 / max(h, w))
    if scale < 1.0:
        from skimage.transform import resize as sk_resize
        small = sk_resize(image, (int(h * scale), int(w * scale)),
                          anti_aliasing=True, preserve_range=True)
    else:
        small = image.copy()

    # Contrast-stretch so faint bands become visible
    alpha, beta = auto_contrast_stretch(small)
    small = np.clip(small * alpha + beta, 0.0, 1.0)

    # Invert: bands become bright peaks, easier for edge detection
    small = 1.0 - small

    # Horizontal Sobel edges — strong at top/bottom of horizontal bands
    edges = np.abs(sobel(small, axis=0))

    # Sweep angles, maximise projection variance
    angles = np.arange(-angle_range, angle_range + angle_step, angle_step)
    best_angle = 0.0
    best_var = -1.0

    for angle in angles:
        if abs(angle) < 1e-3:
            rotated = edges
        else:
            rotated = sk_rotate(edges, angle, resize=False,
                                mode="constant", cval=0.0, preserve_range=True)
        proj = rotated.sum(axis=1)
        var = float(np.var(proj))
        if var > best_var:
            best_var = var
            best_angle = float(angle)

    if abs(best_angle) < angle_step:
        return 0.0
    return round(best_angle, 2)


def auto_crop_to_bands(
    image: NDArray[np.float64],
    dark_threshold: float = 0.85,
    min_band_width_frac: float = 0.3,
    padding_frac: float = 0.08,
) -> NDArray[np.float64]:
    """Crop the image vertically to the region containing bands.

    Finds rows where a significant fraction of pixels are darker than
    ``dark_threshold`` (i.e. contain band content) and crops to that
    vertical span plus a padding margin.

    Works on dark-on-white images (bands are dark = low pixel value).

    Args:
        image: Grayscale float64 image in [0.0, 1.0].
        dark_threshold: Pixels below this value are considered band content.
        min_band_width_frac: A row is considered a "band row" only if
            at least this fraction of its pixels are dark. Prevents
            isolated dust/specs from expanding the crop region.
        padding_frac: Fraction of the detected band height to add as
            padding above and below the crop.

    Returns:
        Vertically cropped image. If no band content is found, the
        original image is returned unchanged.
    """
    h, w = image.shape[:2]

    # For each row, compute the fraction of pixels below threshold
    dark_frac = np.mean(image < dark_threshold, axis=1)  # shape (h,)

    band_rows = np.where(dark_frac >= min_band_width_frac)[0]

    if len(band_rows) == 0:
        return image  # nothing found — return original

    r_min = int(band_rows[0])
    r_max = int(band_rows[-1])

    # Add padding
    band_span = max(r_max - r_min, 1)
    pad = int(band_span * padding_frac)
    r_min = max(0, r_min - pad)
    r_max = min(h, r_max + pad + 1)

    return image[r_min:r_max, :]


def calculate_autocrop_region(
    image: NDArray[np.float64],
    threshold: float = 0.95,
    padding: int = 10,
) -> Optional[tuple[int, int, int, int]]:
    """Calculate the autocrop region without applying it.
    
    Returns the crop rectangle (x, y, width, height) that would be used
    by crop_to_content, allowing for preview visualization.
    
    Args:
        image: Grayscale float64 image in [0.0, 1.0].
        threshold: Pixel values above this are considered background.
        padding: Number of pixels to keep around the detected content.
    
    Returns:
        Tuple of (x, y, width, height) defining the crop region,
        or None if no content is detected.
    """
    # Find rows and columns with content (below threshold)
    content_mask = image < threshold
    
    # Find bounding box of content
    rows_with_content = np.any(content_mask, axis=1)
    cols_with_content = np.any(content_mask, axis=0)
    
    if not np.any(rows_with_content) or not np.any(cols_with_content):
        return None  # No content detected
    
    row_indices = np.where(rows_with_content)[0]
    col_indices = np.where(cols_with_content)[0]
    
    r_min = max(0, row_indices[0] - padding)
    r_max = min(image.shape[0], row_indices[-1] + padding + 1)
    c_min = max(0, col_indices[0] - padding)
    c_max = min(image.shape[1], col_indices[-1] + padding + 1)
    
    # Return (x, y, width, height)
    return (
        int(c_min),                    # x
        int(r_min),                    # y
        int(c_max - c_min),           # width
        int(r_max - r_min),           # height
    )