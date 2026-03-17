"""Ponceau Stain — Step 3: Band Detection & Loading Factors.

Detects bands in the Ponceau image and computes per-lane loading
factors.  Shows a mini bar chart of factors so the user can visually
verify that loading was reasonably uniform before proceeding.
"""

from __future__ import annotations

import logging

import numpy as np
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from biopro.ui.theme import Colors
from biopro.plugins.western_blot.ui.base import WizardPanel, WizardStep

matplotlib.use("QtAgg")

logger = logging.getLogger(__name__)


class _FactorChart(FigureCanvasQTAgg):
    """Mini bar chart showing per-lane Ponceau loading factors."""

    def __init__(self, parent=None) -> None:
        self.fig = Figure(figsize=(5, 2.2), dpi=90)
        self.fig.patch.set_facecolor(Colors.BG_DARK)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")
        self._draw_empty()

    def _draw_empty(self) -> None:
        self.ax.clear()
        self.ax.set_facecolor(Colors.BG_DARK)
        self.ax.text(
            0.5, 0.5, "Run band detection to see loading factors",
            ha="center", va="center", color=Colors.FG_SECONDARY,
            fontsize=9, transform=self.ax.transAxes,
        )
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        self.fig.tight_layout()
        self.draw()

    def plot_factors(
        self,
        factors: dict[int, float],
        num_lanes: int,
        label_prefix: str = "WB",
    ) -> None:
        self.ax.clear()
        self.ax.set_facecolor(Colors.BG_DARK)

        lanes = list(range(num_lanes))
        values = [factors.get(i, 1.0) for i in lanes]
        labels = [f"{label_prefix} {i + 1}" for i in lanes]

        colors = [
            Colors.ACCENT_PRIMARY if abs(v - 1.0) < 0.15
            else Colors.ACCENT_WARNING if abs(v - 1.0) < 0.35
            else Colors.ACCENT_DANGER
            for v in values
        ]

        bars = self.ax.bar(range(num_lanes), values, color=colors,
                           edgecolor="none", width=0.6, alpha=0.9)

        # Reference line at 1.0
        self.ax.axhline(1.0, color=Colors.FG_SECONDARY, linewidth=0.8,
                        linestyle="--", alpha=0.6)

        for bar, val in zip(bars, values):
            self.ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.2f}",
                ha="center", va="bottom",
                fontsize=7, color=Colors.FG_SECONDARY,
            )

        self.ax.set_xticks(range(num_lanes))
        self.ax.set_xticklabels(labels, fontsize=8, color=Colors.FG_SECONDARY)
        self.ax.set_ylabel("Loading factor", fontsize=8, color=Colors.FG_SECONDARY)
        title = (
            "Ponceau loading factors → WB lanes"
            if label_prefix == "WB"
            else "Ponceau loading factors (WB lanes not yet detected)"
        )
        self.ax.set_title(title,
                          fontsize=9, color=Colors.FG_PRIMARY)
        self.ax.tick_params(colors=Colors.FG_SECONDARY)
        for spine in ("top", "right"):
            self.ax.spines[spine].set_visible(False)
        for spine in ("bottom", "left"):
            self.ax.spines[spine].set_color(Colors.BORDER)

        self.fig.tight_layout()
        self.draw()


class PonceauBandsStep(WizardStep):
    """Detect Ponceau bands and preview loading factors."""

    label = "Pon. Bands"

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._active_dialog = None

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # Quantification mode
        mode_group = QGroupBox("Quantification Mode")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(6)

        mode_hint = QLabel(
            "Reference band: pick one prominent band per lane (matches ImageJ protocol).\n"
            "Total lane: sum all detected bands — more statistically robust."
        )
        mode_hint.setWordWrap(True)
        mode_hint.setObjectName("subtitle")
        mode_layout.addWidget(mode_hint)

        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Reference band (per-lane)", "Total lane intensity"])
        self.combo_mode.setCurrentIndex(0)   # Reference band = default (prof's method)
        self.combo_mode.setToolTip(
            "Reference band: user picks 1 prominent band per lane.\n"
            "Total lane: sum all detected bands (recommended by literature)."
        )
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addLayout(self._row("Mode:", self.combo_mode))
        layout.addWidget(mode_group)

        # Reference band selection status — shown in reference_band mode
        self._ref_group = QGroupBox("Reference Band Selection")
        ref_layout = QVBoxLayout(self._ref_group)
        ref_layout.setSpacing(6)

        ref_instr = QLabel(
            "After detecting bands, click a band on the image canvas to set it "
            "as the reference for that lane.  Click a different band to change it."
        )
        ref_instr.setWordWrap(True)
        ref_instr.setObjectName("subtitle")
        ref_layout.addWidget(ref_instr)

        self.lbl_ref_status = QLabel("(detect bands first)")
        self.lbl_ref_status.setWordWrap(True)
        self.lbl_ref_status.setObjectName("subtitle")
        self.lbl_ref_status.setMinimumHeight(18)
        ref_layout.addWidget(self.lbl_ref_status)

        layout.addWidget(self._ref_group)

        # Detection settings (simplified — Ponceau bands are broad and faint)
        det_group = QGroupBox("Detection Settings")
        det_layout = QVBoxLayout(det_group)
        det_layout.setSpacing(8)

        from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox
        self.spin_snr = QDoubleSpinBox()
        self.spin_snr.setRange(1.0, 10.0)
        self.spin_snr.setValue(2.0)   # Lower default — Ponceau is faint
        self.spin_snr.setSingleStep(0.5)
        self.spin_snr.setToolTip(
            "SNR threshold for Ponceau bands.\n"
            "Lower than WB because Ponceau signal is weaker.\n"
            "• 1.5 = very lenient  • 2.0 = default  • 3.0 = strict"
        )
        det_layout.addLayout(self._row("Min SNR:", self.spin_snr))

        self.spin_min_distance = QSpinBox()
        self.spin_min_distance.setRange(3, 100)
        self.spin_min_distance.setValue(8)
        self.spin_min_distance.setSuffix(" px")
        det_layout.addLayout(self._row("Min spacing:", self.spin_min_distance))

        layout.addWidget(det_group)

        # Actions
        self.btn_detect = QPushButton("🔬  Detect Ponceau Bands")
        self.btn_detect.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f" border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.ACCENT_PRIMARY_PRESSED}; }}"
            f"QPushButton:disabled {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_DISABLED}; }}"
        )
        self.btn_detect.setMinimumHeight(36)
        self.btn_detect.clicked.connect(self._detect_bands)
        layout.addWidget(self.btn_detect)

        self.btn_profiles = QPushButton("📈  View Lane Profiles")
        self.btn_profiles.setMinimumHeight(34)
        self.btn_profiles.clicked.connect(self._show_profiles)
        layout.addWidget(self.btn_profiles)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(18)
        layout.addWidget(self.lbl_status)

        # Loading factor chart
        chart_group = QGroupBox("Loading Factors Preview")
        chart_layout = QVBoxLayout(chart_group)
        self._chart = _FactorChart()
        chart_layout.addWidget(self._chart)

        self.lbl_chart_hint = QLabel(
            "Green bars ≈ 1.0 (well-loaded).  "
            "Amber/red bars indicate unequal loading — "
            "Ponceau normalization will correct for this."
        )
        self.lbl_chart_hint.setWordWrap(True)
        self.lbl_chart_hint.setObjectName("subtitle")
        chart_layout.addWidget(self.lbl_chart_hint)
        layout.addWidget(chart_group)

        layout.addStretch()
        return self._scroll(page)

    def on_enter(self) -> None:
        """Restore the Ponceau image and band overlays on the canvas.

        The canvas may be showing the WB image if the user navigated forward
        from WB steps.  When entering this step we must switch the canvas back
        to the Ponceau image so clicks land on Ponceau bands, not WB bands.
        """
        analyzer = self._panel.ponceau_analyzer
        if analyzer is None:
            return

        # Show Ponceau image on canvas
        if analyzer.state.processed_image is not None:
            self._panel.image_changed.emit(analyzer.state.processed_image)

        # Show Ponceau lane overlays
        if analyzer.state.lanes:
            self._panel.lanes_detected.emit(analyzer.state.lanes)

        # Show Ponceau band overlays so the user can click them
        if analyzer.state.bands:
            self._panel.bands_detected.emit(
                analyzer.state.bands, analyzer.state.lanes
            )
            self._update_chart()
            self._refresh_ref_band_status()

    def on_band_clicked(self, band, panel: WizardPanel) -> None:
        """Handle band click on the image canvas.

        In reference_band mode: set this band as the reference for its lane.
        The chart and status update immediately.
        In total mode: just show band info — no reference selection needed.
        """
        if panel.ponceau_analyzer is None:
            return

        mode = panel.ponceau_analyzer.mode
        lane_idx = band.lane_index

        if mode == "reference_band":
            # Register this band as the reference for its lane
            panel.ponceau_analyzer.ref_band_indices[lane_idx] = band.band_index
            panel.status_message.emit(
                f"Ponceau reference band set: Lane {lane_idx + 1}, "
                f"band {band.band_index + 1}, "
                f"intensity {band.integrated_intensity:.3f}"
            )
            self._update_chart()
            self._refresh_ref_band_status()
        else:
            panel.status_message.emit(
                f"Ponceau band: Lane {lane_idx + 1}, "
                f"pos {band.position}, "
                f"intensity {band.integrated_intensity:.3f}"
            )

    def _refresh_ref_band_status(self) -> None:
        """Update the reference band selection summary label."""
        if not hasattr(self, "lbl_ref_status"):
            return
        analyzer = self._panel.ponceau_analyzer
        if analyzer is None or analyzer.mode != "reference_band":
            self.lbl_ref_status.setText("")
            return

        lanes = analyzer.state.lanes
        if not lanes:
            return

        lines = []
        all_set = True
        for lane in lanes:
            idx = lane.index
            lane_bands = [b for b in analyzer.state.bands if b.lane_index == idx]
            if not lane_bands:
                lines.append(f"Lane {idx + 1}: no bands (will use total lane fallback)")
                all_set = False
                continue
            ref_idx = analyzer.ref_band_indices.get(idx)
            if ref_idx is None:
                lines.append(f"Lane {idx + 1}: ⚠️ not set — click a band on the image")
                all_set = False
            else:
                ref_bands = [b for b in lane_bands if b.band_index == ref_idx]
                if ref_bands:
                    b = ref_bands[0]
                    lines.append(
                        f"Lane {idx + 1}: ✅ band {ref_idx + 1} "
                        f"(pos {b.position}, int {b.integrated_intensity:.3f})"
                    )
                else:
                    lines.append(f"Lane {idx + 1}: ⚠️ band {ref_idx + 1} not found")
                    all_set = False

        self.lbl_ref_status.setText("\n".join(lines))
        if all_set:
            self.lbl_ref_status.setStyleSheet(f"color: {Colors.SUCCESS};")
        elif any("\u26a0" in l for l in lines):
            self.lbl_ref_status.setStyleSheet(f"color: {Colors.ACCENT_WARNING};")
        else:
            self.lbl_ref_status.setStyleSheet(f"color: {Colors.FG_SECONDARY};")

    def on_next(self, panel: WizardPanel) -> bool:
        if not panel.ponceau_analyzer.state.bands:
            self._detect_bands()
        if not panel.ponceau_analyzer.state.bands:
            panel.status_message.emit("No Ponceau bands detected — check contrast/SNR settings.")
            return False
        # Write mode to analyzer
        self._sync_mode(panel)
        return True

    # ── Detection ─────────────────────────────────────────────────────

    def _detect_bands(self) -> None:
        try:
            # Clear stale reference band indices — old band indices are
            # invalidated whenever detection re-runs and bands get re-indexed.
            self._panel.ponceau_analyzer.ref_band_indices.clear()

            bands = self._panel.ponceau_analyzer.detect_bands(
                min_snr=self.spin_snr.value(),
                min_peak_distance=self.spin_min_distance.value(),
                force_valleys_as_bands=None,  # auto-detect polarity
            )
            n = len(bands)
            self.lbl_status.setText(f"✅  {n} Ponceau bands detected")
            self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            self._panel.status_message.emit(f"Ponceau: {n} bands detected")
            self._panel.bands_detected.emit(
                bands, self._panel.ponceau_analyzer.state.lanes
            )
            self._sync_mode(self._panel)
            self._update_chart()
            self._refresh_ref_band_status()
        except Exception as e:
            self.lbl_status.setText(f"❌  {e}")
            self.lbl_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Ponceau band detection error")

    def _on_mode_changed(self, _idx: int) -> None:
        self._sync_mode(self._panel)
        if self._panel.ponceau_analyzer.state.bands:
            self._update_chart()

    def _sync_mode(self, panel: WizardPanel) -> None:
        mode = "reference_band" if self.combo_mode.currentIndex() == 0 else "total"
        panel.ponceau_analyzer.mode = mode
        self._ref_group.setVisible(mode == "reference_band")
        self._refresh_ref_band_status()

    def _update_chart(self) -> None:
        try:
            nb_wb = len(self._panel.analyzer.state.lanes)
            if nb_wb > 0:
                # WB lanes are known — show WB-mapped factors
                factors = self._panel.ponceau_analyzer.get_wb_loading_factors(nb_wb)
                self._chart.plot_factors(factors, nb_wb, label_prefix="WB")
            else:
                # WB lanes not yet detected — show Ponceau lane factors directly
                factors = self._panel.ponceau_analyzer.get_loading_factors()
                nb_pon = len(self._panel.ponceau_analyzer.state.lanes)
                if nb_pon > 0 and factors:
                    # Ensure all lanes present (factor 1.0 for any missing)
                    full = {i: factors.get(i, 1.0) for i in range(nb_pon)}
                    self._chart.plot_factors(full, nb_pon, label_prefix="Pon.")
        except Exception as e:
            logger.warning("Could not update Ponceau chart: %s", e)

    # ── Profile viewer ─────────────────────────────────────────────────

    def _show_profiles(self) -> None:
        from biopro.ui.lane_profile_dialog import LaneProfileDialog
        analyzer = self._panel.ponceau_analyzer
        if not analyzer.state.profiles:
            try:
                self._detect_bands()
            except Exception as e:
                self._panel.status_message.emit(f"Could not compute profiles: {e}")
                return

        dialog = LaneProfileDialog(analyzer.state, None)
        self._active_dialog = dialog

        dialog.profile_hovered.connect(
            lambda li, y: self._panel.profile_hovered.emit(li, y)
        )
        dialog.profile_clicked.connect(self._on_profile_clicked)
        dialog.profile_band_removed.connect(self._on_profile_band_removed)

        dialog.exec()
        self._active_dialog = None
        # Refresh chart after manual edits
        if analyzer.state.bands:
            self._update_chart()

    def _on_profile_clicked(self, lane_idx: int, y_pos: float) -> None:
        rel_y = int(round(float(y_pos)))
        if rel_y < 0:
            return
        try:
            self._panel.ponceau_analyzer.add_manual_band(lane_idx, rel_y)
        except Exception as e:
            self._panel.status_message.emit(f"Error adding band: {e}")
            return
        if self._active_dialog is not None:
            self._active_dialog._update_plot()
        self._update_chart()

    def _on_profile_band_removed(self, lane_idx: int, y_pos: float) -> None:
        if self._panel.ponceau_analyzer.remove_band_at(lane_idx, y_pos):
            self._panel.status_message.emit(f"Removed Ponceau band in lane {lane_idx + 1}")
            if self._active_dialog is not None:
                self._active_dialog._update_plot()
            self._update_chart()