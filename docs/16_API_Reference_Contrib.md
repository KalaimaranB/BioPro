# 📖 BioPro SDK API Reference: Contrib (`biopro.sdk.contrib`)

This document provides formal technical specifications for the optional scientific and image-processing utilities within the `biopro.sdk.contrib` namespace.

---

## 🔬 Image Utilities

These functions assist in processing, loading, and segmenting high-resolution scientific image data (such as Western Blot TIF blots or Cytometry cell images).

##### `load_and_convert(path: str, as_grayscale: bool = False) -> np.ndarray`
Loads an image file into a highly-optimized NumPy float array normalized to the range `[0.0, 1.0]`.
* **Parameters:**
  * `path` (str): Absolute file path to the image.
  * `as_grayscale` (bool, optional): Converts multi-channel RGB to single-channel grayscale if `True`. Defaults to `False`.
* **Returns:** `numpy.ndarray` — Normalized float image array.

##### `adjust_contrast(img: np.ndarray, alpha: float, beta: float) -> np.ndarray`
Modifies image contrast and brightness using a standardized linear gain scaling (`alpha * pixel + beta`).
* **Parameters:**
  * `img` (`numpy.ndarray`): Input normalized float image.
  * `alpha` (float): Contrast multiplier.
  * `beta` (float): Brightness offset.
* **Returns:** `numpy.ndarray` — Contrast-adjusted image.

##### `invert_image(img: np.ndarray) -> np.ndarray`
Performs a fast bitwise inversion (`1.0 - pixel`) for normalized image representations.
* **Parameters:**
  * `img` (`numpy.ndarray`): Input normalized float image.
* **Returns:** `numpy.ndarray` — Inverted image array.

##### `auto_detect_inversion(img: np.ndarray) -> bool`
Scans background pixel distributions to auto-detect whether the image is inverted (e.g. light bands on dark background vs dark bands on light background).
* **Returns:** `bool` — `True` if inversion is detected.

##### `enhance_for_band_detection(img: np.ndarray) -> np.ndarray`
Applies contrast amplification and background noise reduction tailored specifically for identifying Western Blot protein bands.
* **Returns:** `numpy.ndarray` — Enhanced image array.

##### `rotate_image(img: np.ndarray, angle: float) -> np.ndarray`
Rotates the target image by the specified angle in degrees (clockwise).
* **Parameters:**
  * `img` (`numpy.ndarray`): Input image array.
  * `angle` (float): Rotation angle in degrees.
* **Returns:** `numpy.ndarray` — Rotated image array.

##### `crop_to_content(img: np.ndarray, padding: int = 10) -> np.ndarray`
Automatically crops out solid-colored margins around the main subject content (using simple threshold contours), leaving a safe boundary padding.
* **Parameters:**
  * `img` (`numpy.ndarray`): Input image array.
  * `padding` (int, optional): Safe margin padding in pixels. Defaults to `10`.
* **Returns:** `numpy.ndarray` — Cropped image content.

---

## 💻 Full Code Example

```python
import numpy as np
from biopro.sdk.contrib import load_and_convert, enhance_for_band_detection, crop_to_content

def process_raw_gel_blot(file_path: str) -> np.ndarray:
    # 1. Load and normalize raw file to [0.0, 1.0] grayscale float64
    raw_img = load_and_convert(file_path, as_grayscale=True)

    # 2. Amplify signal bands and suppress background noise
    enhanced_img = enhance_for_band_detection(raw_img)

    # 3. Trim out empty margins around the blot
    cropped_result = crop_to_content(enhanced_img, padding=15)

    return cropped_result
```
