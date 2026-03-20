# 🎞️ Western Blot Pro: Automated Densitometry

This module provides a high-precision pipeline for quantifying Western Blot and Ponceau S stains. It replicates the gold-standard ImageJ protocol while removing human bias through automated peak-finding and dynamic lane mapping.

## 📖 Deep Dive: How it Works

BioPro treats your gel image as a series of 1D signals. To achieve this, it uses a multi-stage mathematical engine.

### 1. 1D Projection Analysis
For every lane you define, BioPro calculates a "Profile." This is done by averaging the horizontal pixel intensities across the width of the lane at every vertical coordinate ($y$). 

By averaging across the lane width, we significantly increase the **Signal-to-Noise Ratio (SNR)**, making faint bands stand out more clearly than they do in a single-pixel line scan.

### 2. The Rolling Ball Algorithm
Background noise in Western Blots is rarely flat (it’s often a "gradient" or "splotchy"). BioPro uses a **Rolling Ball** algorithm for background subtraction.

Mathematically, a virtual circle of radius $r$ is "rolled" underneath the profile curve. The path traced by the top of the ball becomes your **Baseline**. Any intensity below this line is discarded as background noise, ensuring that your measurements represent true protein signal.

### 3. Area Integration (AUC)
The final intensity ($I$) is the **Area Under the Curve**. BioPro calculates the definite integral of the peak $P(y)$ minus the baseline $B(y)$:


$$I = \int_{y_{start}}^{y_{end}} (P(y) - B(y)) \,dy$$

This is the mathematical equivalent of the ImageJ "Wand Tool" area, but with the baseline drawn with 100% geometric consistency every time.

---

## 🏗️ Step-by-Step Guide & Pro-Tips

### Step 1: Image Setup
* **Auto-Inversion:** BioPro checks the "mean intensity" of the image edges. If the edges are brighter than the center, it assumes a light background and flips the LUT. 
* **Critical Rotation:** If your lanes are even 2° crooked, a vertical slice will "cut through" the side of a band instead of the center. Use the slider until the lanes look perfectly parallel to the sidebar.

### Step 2: Lane Detection
* **Gaps Matter:** When dragging lane boxes, try to center them on the bands. 
* **Dynamic Boundaries:** BioPro doesn't just look at where you draw the box; it analyzes the "valleys" between lanes to ensure signal from Lane 1 doesn't bleed into Lane 2.

### Step 3: Band Detection
* **SNR Threshold:** High SNR (e.g., 5.0) only finds the strongest bands. Low SNR (e.g., 2.0) finds faint bands but may pick up "ghost" noise.
* **Refining with Clicks:**
    * **Left-Click:** Snaps to the nearest local maximum (the darkest part of the band).
    * **Shift + Drag:** Manually defines the start ($y_1$) and end ($y_2$) for integration. Use this for "smeared" bands where a single peak doesn't exist.
    * **Right-Click:** Instantly removes a band marker (▲).

### Step 4: Ponceau Normalization
BioPro offers two ways to correct for loading errors:
1.  **Reference Band:** You pick a "housekeeping" protein (like Actin or GAPDH) in the Ponceau stain. All WB data is divided by the intensity of this specific band.
2.  **Total Lane:** The app sums the intensity of *every* detected band in the Ponceau lane. This is often more accurate as it accounts for the entire protein load, not just one potentially saturated band.

---

## 🧪 Understanding the Data Dictionary

| Column | Formula | Description |
| :--- | :--- | :--- |
| **WB Raw Intensity** | $\int (P-B)dy$ | The raw "signal" of your target protein. |
| **Ponceau Raw** | $I_{loading}$ | The "weight" of the lane (Reference or Total). |
| **WB/Pon Ratio** | $\frac{I_{WB}}{I_{Pon}}$ | The loading-corrected signal. **Use this for your stats.** |
| **Normalized** | $\frac{Ratio_{Sample}}{Ratio_{Control}}$ | Relative fold-change. Your control lane will always be **1.00**. |

---

### Why use this over ImageJ?
ImageJ requires "subjective thresholding"—you decide where the baseline starts and ends by eye. If you're tired or biased, you might draw the line slightly lower for a "key" sample. **BioPro is an objective judge.** It treats every pixel and every lane with the exact same geometric rules, making your data 100% reproducible for publication.