"""Generate BioPro pipeline illustration figures for the README."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle, FancyBboxPatch
from scipy.ndimage import uniform_filter1d
from scipy.signal import find_peaks
from pathlib import Path

OUT = Path(".")
OUT.mkdir(exist_ok=True)

DARK   = "#161b22"
MED    = "#21262d"
LIGHT  = "#30363d"
FG     = "#e6edf3"
FG2    = "#8b949e"
TEAL   = "#2dccb8"
BLUE   = "#58a6ff"
AMBER  = "#d29922"
RED    = "#f85149"
GREEN  = "#3fb950"

plt.rcParams.update({
    "figure.facecolor": DARK, "axes.facecolor": MED,
    "text.color": FG, "axes.labelcolor": FG,
    "xtick.color": FG2, "ytick.color": FG2,
    "axes.edgecolor": LIGHT, "axes.spines.top": False,
    "axes.spines.right": False, "font.family": "DejaVu Sans",
})


# ── Figure 1: Pipeline overview flowchart ────────────────────────────────────
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(14, 3.5))
    fig.patch.set_facecolor(DARK)
    ax.set_facecolor(DARK)
    ax.axis("off")

    steps = [
        ("1. Load\nImage", TEAL),
        ("2. Preprocess\n(invert/rotate/\ncontrast/crop)", BLUE),
        ("3. Detect\nLanes", "#a371f7"),
        ("4. Detect\nBands", AMBER),
        ("5. Compute\nDensitometry", RED),
        ("6. Ponceau\nNormalise", GREEN),
        ("7. Results\n& Export", TEAL),
    ]

    n = len(steps)
    xs = np.linspace(0.04, 0.96, n)
    y  = 0.5
    bw, bh = 0.10, 0.55

    for i, (label, color) in enumerate(steps):
        x = xs[i]
        box = FancyBboxPatch(
            (x - bw/2, y - bh/2), bw, bh,
            boxstyle="round,pad=0.02",
            facecolor=color + "33", edgecolor=color, linewidth=2,
        )
        ax.add_patch(box)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=8.5, color=FG, fontweight="bold",
                multialignment="center")

        if i < n - 1:
            x1, x2 = x + bw/2 + 0.005, xs[i+1] - bw/2 - 0.005
            ax.annotate("", xy=(x2, y), xytext=(x1, y),
                        arrowprops=dict(arrowstyle="->", color=FG2, lw=1.5))

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("BioPro Western Blot Analysis Pipeline", color=FG,
                 fontsize=12, fontweight="bold", pad=8)
    fig.tight_layout()
    fig.savefig(OUT / "01_pipeline_overview.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 1 done")


# ── Figure 2: Image layer model ───────────────────────────────────────────────
def fig_layer_model():
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.8))
    fig.patch.set_facecolor(DARK)

    rng = np.random.default_rng(42)
    H, W = 120, 80

    # Raw: bright background, 3 dark bands
    raw = np.ones((H, W)) * 0.85 + rng.normal(0, 0.03, (H, W))
    for y in [25, 55, 85]:
        raw[y-6:y+6, 8:72] = 0.15 + rng.normal(0, 0.02, (12, 64))
    raw = np.clip(raw, 0, 1)

    # Base: inverted + slight rotation simulation (just brighter bands)
    base = 1 - raw
    base = np.clip(base * 1.5 - 0.3, 0, 1)

    # Processed: cropped
    processed = base[10:110, 5:75]

    # Display: same as processed (visual)
    display = processed.copy()

    labels = ["raw_image\n(disk pixels,\nnever modified)",
              "base_image\n(inverted + contrast\n+ rotated, no crop)",
              "processed_image\n(crop applied —\nused for analysis)",
              "canvas display\n(what you see\nin the UI)"]
    colors = [FG2, BLUE, TEAL, GREEN]
    imgs   = [raw, base, processed, display]

    for ax, img, lbl, col in zip(axes, imgs, labels, colors):
        ax.imshow(img, cmap="gray", vmin=0, vmax=1, aspect="auto")
        ax.set_title(lbl, color=col, fontsize=8, fontweight="bold",
                     multialignment="center")
        for sp in ax.spines.values():
            sp.set_edgecolor(col); sp.set_linewidth(2)
        ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle("Three-Layer Image Model (Phase 4)", color=FG,
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "02_image_layers.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 2 done")


# ── Figure 3: Lane detection ──────────────────────────────────────────────────
def fig_lane_detection():
    rng = np.random.default_rng(7)
    H, W = 200, 320
    img = np.ones((H, W)) * 0.9 + rng.normal(0, 0.02, (H, W))
    lane_centers = [45, 115, 185, 255]
    lane_w = 40
    for cx in lane_centers:
        for y in [40, 90, 140, 170]:
            img[y-8:y+8, cx-lane_w//2:cx+lane_w//2] = (
                0.2 + rng.normal(0, 0.03, (16, lane_w))
            )
    img = np.clip(img, 0, 1)

    projection = np.mean(img, axis=0)
    smoothed   = uniform_filter1d(projection, size=15)
    peaks, _   = find_peaks(smoothed, distance=10, prominence=0.01)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6),
                                    gridspec_kw={"height_ratios": [3, 1.5]})
    fig.patch.set_facecolor(DARK)

    ax1.imshow(img, cmap="gray", aspect="auto")
    colors4 = [TEAL, BLUE, AMBER, GREEN]
    for i, (left, right) in enumerate(zip(
        [0] + list(peaks), list(peaks) + [W]
    )):
        ax1.axvspan(left, right, alpha=0.18, color=colors4[i % 4])
        ax1.text((left+right)/2, 10, str(i+1), ha="center", va="top",
                 color=colors4[i % 4], fontsize=14, fontweight="bold")
    for p in peaks:
        ax1.axvline(p, color=FG2, lw=1.5, linestyle="--", alpha=0.7)
    ax1.set_title("Lane Detection — Otsu + vertical projection", color=FG,
                  fontsize=10)
    ax1.set_xticks([]); ax1.set_yticks([])

    ax2.plot(projection, color=FG2, lw=1, alpha=0.5, label="Raw projection")
    ax2.plot(smoothed, color=TEAL, lw=2, label="Smoothed")
    for p in peaks:
        ax2.axvline(p, color=AMBER, lw=1.5, linestyle="--", alpha=0.8)
    ax2.scatter(peaks, smoothed[peaks], color=RED, s=60, zorder=5,
                label="Gap peaks")
    ax2.set_ylabel("Mean intensity", fontsize=8)
    ax2.set_xlabel("Column (x pixel)", fontsize=8)
    ax2.legend(fontsize=7, facecolor=MED, edgecolor=LIGHT)
    ax2.set_xlim(0, W)

    fig.tight_layout()
    fig.savefig(OUT / "03_lane_detection.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 3 done")


# ── Figure 4: Band detection / profile analysis ───────────────────────────────
def fig_band_detection():
    n = 300
    x = np.linspace(0, 1, n)

    # Simulate a lane profile: bands as dips in a light background
    background = 0.75 + 0.06 * np.sin(np.pi * x)
    bands_signal = np.zeros(n)
    for center, amp, width in [(0.18, 0.45, 18), (0.42, 0.55, 22),
                                 (0.65, 0.30, 14), (0.83, 0.38, 16)]:
        ci = int(center * n)
        wi = width
        bands_signal += amp * np.exp(-0.5 * ((np.arange(n) - ci) / wi)**2)
    raw_profile = np.clip(background - bands_signal + np.random.default_rng(3).normal(0, 0.015, n), 0, 1)

    # Inverted (as BioPro processes it — bands become peaks)
    profile = 1 - raw_profile

    # Rolling ball baseline approximation
    from scipy.ndimage import minimum_filter1d
    baseline = minimum_filter1d(profile, size=60)
    baseline = uniform_filter1d(baseline, size=40)
    corrected = np.maximum(profile - baseline, 0)

    noise = float(np.median(np.abs(corrected - np.median(corrected)))) * 1.4826
    threshold = max(0.02, noise * 3.0)

    detected_peaks, props = find_peaks(corrected, height=threshold, distance=20, prominence=threshold*0.5)

    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
    fig.patch.set_facecolor(DARK)
    xi = np.arange(n)

    # Panel 1: raw profile
    axes[0].plot(xi, raw_profile, color=FG2, lw=1.5, label="Raw profile (inverted blot)")
    axes[0].set_ylabel("Intensity", fontsize=8)
    axes[0].set_title("Step 1 — Raw lane profile (middle third of lane width)", fontsize=9, color=FG)
    axes[0].legend(fontsize=8, facecolor=MED)

    # Panel 2: inverted + baseline
    axes[1].plot(xi, profile,  color=BLUE, lw=1.5, label="After inversion (bands = peaks)")
    axes[1].plot(xi, baseline, color=RED,  lw=2, linestyle="--", label="Rolling-ball baseline")
    axes[1].fill_between(xi, baseline, profile, where=(profile > baseline),
                          alpha=0.15, color=TEAL, label="Area above baseline")
    axes[1].set_ylabel("Intensity", fontsize=8)
    axes[1].set_title("Step 2 — Baseline estimation (rolling-ball algorithm)", fontsize=9, color=FG)
    axes[1].legend(fontsize=8, facecolor=MED)

    # Panel 3: corrected + detected peaks
    axes[2].plot(xi, corrected, color=TEAL, lw=2, label="Baseline-corrected signal")
    axes[2].axhline(threshold, color=AMBER, lw=1.5, linestyle=":", label=f"SNR threshold (noise×3)")
    for i, pk in enumerate(detected_peaks):
        h = corrected[pk]
        w_est = props.get("widths", [14]*len(detected_peaks))
        hw = 7
        axes[2].fill_between(xi[max(0,pk-hw):pk+hw+1],
                              corrected[max(0,pk-hw):pk+hw+1],
                              alpha=0.35, color=GREEN)
        axes[2].plot(pk, h, "o", color=GREEN, ms=8, zorder=6)
        axes[2].annotate(f"Band {i+1}\n∫={corrected[max(0,pk-hw):pk+hw+1].sum():.1f}",
                         xy=(pk, h), xytext=(pk+8, h+0.02),
                         color=GREEN, fontsize=7,
                         arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.8))
    axes[2].set_ylabel("Corrected intensity", fontsize=8)
    axes[2].set_xlabel("Position in lane (pixels, top→bottom)", fontsize=8)
    axes[2].set_title("Step 3 — Peak detection & area integration", fontsize=9, color=FG)
    axes[2].legend(fontsize=8, facecolor=MED)

    fig.suptitle("Band Detection Pipeline (per lane)", color=FG, fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "04_band_detection.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 4 done")


# ── Figure 5: Professor's normalisation method ────────────────────────────────
def fig_normalisation():
    lanes = ["Lane 1\n(Control)", "Lane 2\n(Sample A)", "Lane 3\n(Sample B)"]
    wb_raw  = np.array([850, 1200, 640])
    pon_raw = np.array([920, 950, 870])
    ratio   = wb_raw / pon_raw
    norm    = ratio / ratio[0]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    fig.patch.set_facecolor(DARK)
    colors = [RED, BLUE, GREEN]

    # WB raw
    axes[0].bar(lanes, wb_raw, color=[c+"99" for c in colors], edgecolor=colors, lw=2)
    for i, v in enumerate(wb_raw):
        axes[0].text(i, v + 20, str(int(v)), ha="center", color=colors[i], fontsize=10, fontweight="bold")
    axes[0].set_title("WB Band\nIntensity (arbitrary units)", color=FG, fontsize=10)
    axes[0].set_ylabel("Integrated intensity", fontsize=8)

    # Ponceau raw
    axes[1].bar(lanes, pon_raw, color=[c+"66" for c in colors], edgecolor=colors, lw=2, hatch="//")
    for i, v in enumerate(pon_raw):
        axes[1].text(i, v + 10, str(int(v)), ha="center", color=colors[i], fontsize=10)
    axes[1].set_title("Ponceau Reference Band\nIntensity (same lane)", color=FG, fontsize=10)
    axes[1].set_ylabel("Integrated intensity", fontsize=8)

    # Final ratio
    axes[2].bar(lanes, norm, color=colors, edgecolor=[c+"cc" for c in colors], lw=2, alpha=0.9)
    for i, v in enumerate(norm):
        axes[2].text(i, v + 0.02, f"{v:.3f}", ha="center", color=colors[i],
                     fontsize=11, fontweight="bold")
    axes[2].axhline(1.0, color=FG2, lw=1.2, linestyle="--", alpha=0.6)
    axes[2].set_title("Final: WB/Ponceau Ratio\n(control normalised to 1.0)", color=FG, fontsize=10)
    axes[2].set_ylabel("Normalised ratio", fontsize=8)

    # Annotate formula
    fig.text(0.5, 0.02,
             "Formula:  ratio = WB_band_intensity / Ponceau_ref_band_intensity   "
             "→   normalised = ratio / control_ratio",
             ha="center", color=TEAL, fontsize=9, style="italic")

    for ax in axes:
        ax.tick_params(colors=FG2)
        for sp in ("top","right"): ax.spines[sp].set_visible(False)
        for sp in ("bottom","left"): ax.spines[sp].set_edgecolor(LIGHT)

    fig.suptitle("Professor's Intra-Lane Normalisation Method", color=FG,
                 fontsize=12, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(OUT / "05_normalisation.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 5 done")


# ── Figure 6: Comparison with ImageJ workflow ─────────────────────────────────
def fig_imagej_comparison():
    fig, ax = plt.subplots(figsize=(13, 5.5))
    fig.patch.set_facecolor(DARK)
    ax.axis("off")

    cols = ["Step", "ImageJ Method", "BioPro Method", "Difference"]
    rows = [
        ["Image\nformat",     "File > Open → any format",
         "File picker → TIFF/PNG/JPG/BMP;\nauto convert to float64 [0,1]",
         "✅ Equivalent"],
        ["LUT\nInversion",    "Image → LUT → Invert LUT\n(manual decision)",
         "Auto-detect via median heuristic;\nmanual override available",
         "✅ BioPro automates"],
        ["Greyscale",         "Image → Type → 8-bit\n(irreversible, 256 levels)",
         "float64 [0,1] internally;\n~65000 effective levels",
         "✅ BioPro higher precision"],
        ["Rotation\n& Crop",  "Image → Transform → Rotate;\nRectangular selection + crop",
         "Rotation spinbox + quick ±45/90° buttons;\nmanual draw or auto-crop",
         "✅ Equivalent + more control"],
        ["Lane\nSelection",   "Draw rectangle over 1/3 of lane;\npress 1, drag, press 2…",
         "Auto-detect via Otsu + projection;\ndraggable border lines",
         "✅ BioPro more automated"],
        ["Profile\nExtraction","Analyze > Gels > Plot Lanes;\nmiddle ~33% of lane width",
         "extract_lane_profile() — median\nof middle 50% of lane width",
         "⚠️  BioPro uses 50% not 33%"],
        ["Baseline\nClosure",  "Manual straight-line tool\nto close each peak",
         "Rolling-ball algorithm\n(automatic, per-lane)",
         "⚠️  BioPro automates — less\nuser control per peak"],
        ["Area\nIntegration", "Wand tool click; area\nabove drawn baseline",
         "Scipy find_peaks + trapezoid\nintegration above rolling baseline",
         "✅ Equivalent method"],
        ["Normalisation",     "Excel: WB_peak / Ponceau_peak\nper lane; control=1.0",
         "wb_results._compute_results():\nidentical formula, fully automated",
         "✅ Identical formula"],
    ]

    col_x = [0.01, 0.13, 0.44, 0.75]
    col_w = [0.11, 0.30, 0.30, 0.24]
    row_h = 0.095
    y0    = 0.96

    # Header
    for j, (cx, cw, lbl) in enumerate(zip(col_x, col_w, cols)):
        ax.add_patch(Rectangle((cx, y0-row_h*0.9), cw-0.005, row_h*0.85,
                                fc=TEAL+"44", ec=TEAL, lw=1.5))
        ax.text(cx + cw/2, y0-row_h*0.45, lbl, ha="center", va="center",
                color=TEAL, fontsize=9, fontweight="bold")

    for i, row in enumerate(rows):
        y = y0 - row_h * (i + 1)
        bg = MED if i % 2 == 0 else DARK
        for j, (cx, cw, cell) in enumerate(zip(col_x, col_w, row)):
            ax.add_patch(Rectangle((cx, y-row_h*0.9), cw-0.005, row_h*0.88,
                                    fc=bg, ec=LIGHT, lw=0.8))
            color = FG if j < 3 else (GREEN if "✅" in cell else AMBER)
            ax.text(cx + 0.006, y - row_h*0.45, cell,
                    va="center", color=color, fontsize=7.5,
                    multialignment="left")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("BioPro vs ImageJ — Step-by-step comparison", color=FG,
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "06_imagej_comparison.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 6 done")


# ── Figure 7: Known issues & improvement roadmap ─────────────────────────────
def fig_roadmap():
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(DARK)
    ax.axis("off")

    items = {
        "🐛  Active Bugs": ([
            "integrated_intensity = 0 when rolling-ball baseline ≈ peak height\n→ Fix: use peak_height as fallback (wb_results.py, ponceau.py)",
            "Ponceau loading factors all = 1.0 when ref band intensity = 0\n→ Same root cause as above",
            "Auto-compute on results step fires before band selection is complete\n→ Fix: defer until user clicks Compute, or add debounce",
        ], RED),
        "⚡  UI Issues": ([
            "Results panel: slot selections lost on Compute (partially fixed)\n→ Need _update_canvas_markers() after restore",
            "Band highlight markers clear when Compute Results fires\n→ Fixed in latest results_widget.py",
            "Ponceau autocrop numpy.bool_ ambiguity error\n→ Fixed: cast region elements to int()",
        ], AMBER),
        "🔧  Code Refactoring": ([
            "WBLoadStep and PonceauLoadStep are ~95% identical\n→ Extract BaseLoadStep with subclassing",
            "WBLanesStep and PonceauLanesStep share drag/detect logic\n→ Extract BaseLanesStep",
            "Duplicate AnalysisState dataclass in western_blot.py (removed in Phase 4)\n→ Done ✅",
            "wb_results._compute_results mixes UI logic and science\n→ Move ratio computation to ponceau.py/western_blot.py",
        ], BLUE),
        "✨  Features to Add": ([
            "Undo/Redo (Command/Ctrl+Z) — Action stack per wizard session\n→ Requires Action ABC + ActionHistory on WizardPanel",
            "Auto-compute results when all band slots are filled\n→ Trigger _compute_results() when last slot is assigned",
            "Drag-select band range on image canvas (draw band tool)\n→ Planned in Phase 5",
            "Band overlap detection and merge\n→ When two bands are within min_peak_distance, keep highest",
        ], GREEN),
    }

    y = 0.97
    for section, (lines, color) in items.items():
        ax.text(0.01, y, section, color=color, fontsize=10, fontweight="bold")
        y -= 0.04
        for line in lines:
            ax.text(0.03, y, f"• {line}", color=FG, fontsize=8, va="top",
                    multialignment="left")
            y -= 0.05
        y -= 0.01

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("Known Issues & Improvement Roadmap", color=FG,
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "07_roadmap.png", dpi=150, bbox_inches="tight",
                facecolor=DARK)
    plt.close()
    print("Fig 7 done")


if __name__ == "__main__":
    fig_pipeline()
    fig_layer_model()
    fig_lane_detection()
    fig_band_detection()
    fig_normalisation()
    fig_imagej_comparison()
    fig_roadmap()
    print("\nAll figures saved to", OUT)
