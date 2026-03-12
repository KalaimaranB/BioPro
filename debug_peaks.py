import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from biopro.analysis.image_utils import load_and_convert, auto_detect_inversion, invert_image
from biopro.analysis.peak_analysis import analyze_lane, extract_lane_profile, estimate_noise_level
from scipy.ndimage import uniform_filter1d

image_path = "/Users/kalaimaranbalasothy/Library/CloudStorage/OneDrive-UBC/UBC Course Work/Year 3/Semester 2/MICB 323/MICB Results.png"

# Load image
img = load_and_convert(image_path)
print("Auto-inversion:", auto_detect_inversion(img))
if auto_detect_inversion(img):
    img = invert_image(img)

# Approximate lane bounds based on the screenshot (Lane 2)
# The image is 521x726. Lane 2 is in the middle.
x_start = 210
x_end = 310
y_start = 0
y_end = 726

# Run full analysis
profile, baseline, bands = analyze_lane(
    img, lane_index=1,
    x_start=x_start, x_end=x_end,
    y_start=y_start, y_end=y_end,
    min_peak_height=0.02,
    min_snr=3.0,
    min_peak_distance=5,
    max_band_width=80,
    edge_margin_percent=5.0
)

# Plot
plt.figure(figsize=(12, 8))

# Plot 1: Raw vs smoothed vs baseline
plt.subplot(2, 1, 1)
plt.plot(profile, label='Raw Profile', alpha=0.5, color='gray')
smoothed = uniform_filter1d(profile, 3)
plt.plot(smoothed, label='Smoothed Profile', color='blue')
plt.plot(baseline, label='Baseline (Radius 50)', color='red', linestyle='--')
plt.title("Lane 2 Raw Profile and Baseline")
plt.legend()

# Plot 2: Corrected profile with peaks
plt.subplot(2, 1, 2)
corrected = np.maximum(smoothed - baseline, 0)
plt.plot(corrected, label='Corrected Profile', color='black')

noise = estimate_noise_level(smoothed, baseline)
plt.axhline(noise * 3.0, color='orange', linestyle=':', label='SNR=3 Threshold')

for b in bands:
    plt.axvline(b.position, color='green', alpha=0.5)
    plt.plot(b.position, b.peak_height, 'go')
    # Draw width horizontal line
    plt.hlines(b.peak_height/2, b.position - b.width/2, b.position + b.width/2, color='green')

plt.title(f"Baseline Corrected (Noise={noise:.4f}) - Detected {len(bands)} bands")
plt.legend()

plt.tight_layout()
out = "/Users/kalaimaranbalasothy/.gemini/antigravity/brain/58657072-691d-4cbc-b68d-3e60be9a1508/debug_profile.png"
plt.savefig(out)
print(f"Saved {out}")
