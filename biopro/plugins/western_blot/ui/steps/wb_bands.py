"""Western Blot — Step 3: Band Detection."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors
from biopro.plugins.western_blot.ui.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


class WBBandsStep(WizardStep):
    """Detect bands in each lane and allow manual correction."""

    label = "Bands"

    # ── WizardStep interface ──────────────────────────────────────────

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._active_dialog = None

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # ── Detection parameters ──────────────────────────────────────
        band_group = QGroupBox("Detection Parameters")
        band_layout = QVBoxLayout(band_group)
        band_layout.setSpacing(8)

        self.spin_snr = QDoubleSpinBox()
        self.spin_snr.setRange(1.0, 20.0)
        self.spin_snr.setValue(3.0)
        self.spin_snr.setSingleStep(0.5)
        self.spin_snr.setToolTip(
            "Signal-to-noise ratio threshold.\n"
            "• 2.0 = lenient  • 3.0 = default  • 5.0 = strict"
        )
        band_layout.addLayout(self._row("Min SNR:", self.spin_snr))

        self.spin_peak_distance = QSpinBox()
        self.spin_peak_distance.setRange(3, 100)
        self.spin_peak_distance.setValue(10)
        self.spin_peak_distance.setSuffix(" px")
        self.spin_peak_distance.setToolTip("Minimum distance between adjacent bands in pixels.")
        band_layout.addLayout(self._row("Min band spacing:", self.spin_peak_distance))

        self.spin_max_width = QSpinBox()
        self.spin_max_width.setRange(5, 500)
        self.spin_max_width.setValue(80)
        self.spin_max_width.setSuffix(" px")
        self.spin_max_width.setToolTip(
            "Maximum allowed band width — wider peaks are likely background artifacts."
        )
        band_layout.addLayout(self._row("Max band width:", self.spin_max_width))

        self.spin_min_width = QSpinBox()
        self.spin_min_width.setRange(1, 50)
        self.spin_min_width.setValue(3)
        self.spin_min_width.setSuffix(" px")
        self.spin_min_width.setToolTip("Minimum band width — narrower peaks are likely noise spikes.")
        band_layout.addLayout(self._row("Min band width:", self.spin_min_width))

        self.spin_edge_margin = QDoubleSpinBox()
        self.spin_edge_margin.setRange(0.0, 25.0)
        self.spin_edge_margin.setValue(5.0)
        self.spin_edge_margin.setSuffix(" %")
        self.spin_edge_margin.setToolTip(
            "% of lane height at top/bottom to ignore (rotation/crop edge artifacts)."
        )
        band_layout.addLayout(self._row("Edge margin:", self.spin_edge_margin))
        layout.addWidget(band_group)

        # ── Baseline ──────────────────────────────────────────────────
        baseline_group = QGroupBox("Baseline Estimation")
        baseline_layout = QVBoxLayout(baseline_group)
        baseline_layout.setSpacing(8)

        self.combo_baseline = QComboBox()
        self.combo_baseline.addItems(["Rolling Ball", "Linear"])
        self.combo_baseline.setToolTip(
            "Rolling Ball: smooth background subtraction (recommended).\n"
            "Linear: straight-line baseline between peak valleys."
        )
        baseline_layout.addLayout(self._row("Method:", self.combo_baseline))

        self.spin_radius = QSpinBox()
        self.spin_radius.setRange(0, 200)
        self.spin_radius.setValue(0)
        self.spin_radius.setSpecialValueText("Auto")
        self.spin_radius.setSuffix(" px")
        self.spin_radius.setToolTip(
            "Rolling ball radius.\n'Auto' (0) = 40% of lane height per-lane."
        )
        baseline_layout.addLayout(self._row("Radius:", self.spin_radius))
        layout.addWidget(baseline_group)

        # ── Manual peak picking ───────────────────────────────────────
        manual_group = QGroupBox("ImageJ-style Peak Picking")
        manual_layout = QVBoxLayout(manual_group)
        manual_layout.setSpacing(6)

        self.chk_manual_pick = QCheckBox(
            "Manual peak picking (for messy blots with bad auto-detection)"
        )
        self.chk_manual_pick.setChecked(False)
        self.chk_manual_pick.setToolTip(
            "Compute profiles/baselines only, then click on bands to quantify.\n"
            "Mirrors ImageJ's gel workflow."
        )
        self.chk_manual_pick.toggled.connect(self._on_manual_pick_toggled)
        manual_layout.addWidget(self.chk_manual_pick)

        hint = QLabel(
            "Workflow: enable → click 'Detect Bands' (profiles only) → click bands in the image."
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        hint.setMinimumHeight(32)
        manual_layout.addWidget(hint)
        layout.addWidget(manual_group)

        # ── Actions ───────────────────────────────────────────────────
        self.btn_detect = QPushButton("🔬  Detect Bands")
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
        self.btn_profiles.setToolTip(
            "Opens a plot showing the lane density, baseline, and detected peaks."
        )
        self.btn_profiles.clicked.connect(self._show_lane_profiles)
        layout.addWidget(self.btn_profiles)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(18)
        layout.addWidget(self.lbl_status)

        layout.addStretch()
        return self._scroll(page)

    def on_enter(self) -> None:
        pass

    def on_next(self, panel: WizardPanel) -> bool:
        if not panel.analyzer.state.bands:
            self._detect_bands()
        return bool(panel.analyzer.state.bands)

    # ── Detection ─────────────────────────────────────────────────────

    def _detection_params(self) -> dict:
        baseline_text = self.combo_baseline.currentText()
        return dict(
            min_peak_height=0.02,
            min_peak_distance=self.spin_peak_distance.value(),
            min_snr=self.spin_snr.value(),
            max_band_width=self.spin_max_width.value(),
            min_band_width=self.spin_min_width.value(),
            edge_margin_percent=self.spin_edge_margin.value(),
            baseline_method="rolling_ball" if "Rolling" in baseline_text else "linear",
            baseline_radius=self.spin_radius.value(),
        )

    def _detect_bands(self) -> None:
        try:
            manual_pick = self.chk_manual_pick.isChecked()
            bands = self._panel.analyzer.detect_bands(
                **self._detection_params(),
                manual_pick=manual_pick,
                force_valleys_as_bands=None,
            )

            lane_types = self._get_lane_types()
            sample_bands = [
                b for b in bands if lane_types.get(b.lane_index, "Sample") == "Sample"
            ]

            # Per-lane summary
            counts: dict[int, int] = {}
            for b in bands:
                counts.setdefault(b.lane_index, 0)
                counts[b.lane_index] += 1
            summary = " | ".join(
                f"L{i + 1}: {n}{' [' + lane_types.get(i, 'S')[0] + ']' if lane_types.get(i, 'Sample') != 'Sample' else ''}"
                for i, n in sorted(counts.items())
            )

            if manual_pick:
                self.lbl_status.setText(
                    f"✅  Profiles computed. Click bands in the image.\n{summary}"
                )
            else:
                self.lbl_status.setText(
                    f"✅  {len(bands)} bands ({len(sample_bands)} sample)\n{summary}"
                )
            self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            self._panel.status_message.emit(
                f"Detected {len(bands)} bands ({len(sample_bands)} sample)"
            )
            self._panel.bands_detected.emit(bands, self._panel.analyzer.state.lanes)
            self._panel.selected_bands_changed.emit(sample_bands)

        except Exception as e:
            self.lbl_status.setText(f"❌  {e}")
            self.lbl_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Band detection error")

    def _on_manual_pick_toggled(self, enabled: bool) -> None:
        self._panel.peak_picking_enabled.emit(enabled)
        msg = (
            "Manual picking on — click 'Detect Bands' then click bands in the image."
            if enabled else "Manual picking disabled."
        )
        self._panel.status_message.emit(msg)

    # ── Manual band add/remove (from profile dialog and canvas) ────────

    def on_peak_pick_requested(self, x: float, y: float, panel: WizardPanel) -> None:
        if not self.chk_manual_pick.isChecked():
            return
        if not panel.analyzer.state.lanes:
            return
        lane = next(
            (ln for ln in panel.analyzer.state.lanes
             if ln.x_start <= x <= ln.x_end and ln.y_start <= y <= ln.y_end),
            None,
        )
        if lane is None:
            return
        if not panel.analyzer.state.profiles:
            try:
                self._detect_bands()
            except Exception as e:
                panel.status_message.emit(f"Could not compute profiles: {e}")
                return
        rel_y = int(round(float(y) - float(lane.y_start)))
        try:
            band = panel.analyzer.add_manual_band(lane.index, rel_y)
        except Exception as e:
            panel.status_message.emit(f"Error adding manual band: {e}")
            return
        if band is None:
            panel.status_message.emit("No clear peak near click — try closer to the band centre.")
            return
        self._emit_bands_updated(panel)

    def on_band_clicked(self, band, panel: WizardPanel) -> None:
        # Clicking a band highlights it for the fold-change comparison panel.
        # It does NOT toggle analysis inclusion — band stays selected.
        band.selected = True

        # Tell the results widget directly about this click so it can
        # accumulate the last 2 clicked bands for fold-change comparison.
        # We reach the results widget via the results_ready signal chain —
        # use the panel's results_widget reference if available.
        rw = getattr(panel, "_results_widget_ref", None)
        if rw is not None and hasattr(rw, "highlight_band_for_comparison"):
            rw.highlight_band_for_comparison(band)

        panel.status_message.emit(
            f"Band selected: Lane {band.lane_index + 1}, "
            f"pos {band.position}, "
            f"intensity {band.integrated_intensity:.2f}, "
            f"SNR {band.snr:.1f}  —  click another band to compare"
        )

    def _emit_bands_updated(self, panel: WizardPanel) -> None:
        lane_types = self._get_lane_types()
        sample_bands = [
            b for b in panel.analyzer.state.bands
            if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
        ]
        panel.bands_detected.emit(panel.analyzer.state.bands, panel.analyzer.state.lanes)
        panel.selected_bands_changed.emit(sample_bands)

    # ── Profile dialog ────────────────────────────────────────────────

    def _show_lane_profiles(self) -> None:
        from biopro.ui.lane_profile_dialog import LaneProfileDialog
        analyzer = self._panel.analyzer
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
        dialog.profile_range_selected.connect(self._on_profile_range_selected)
        dialog.profile_band_removed.connect(self._on_profile_band_removed)

        dialog.exec()
        self._active_dialog = None

    def _on_profile_clicked(self, lane_idx: int, y_pos: float) -> None:
        if lane_idx < 0 or lane_idx >= len(self._panel.analyzer.state.lanes):
            return
        rel_y = int(round(float(y_pos)))
        if rel_y < 0:
            return
        try:
            band = self._panel.analyzer.add_manual_band(lane_idx, rel_y)
        except Exception as e:
            self._panel.status_message.emit(f"Error adding band from profile: {e}")
            return
        if band is None:
            self._panel.status_message.emit("No clear peak near click.")
            return
        self._emit_bands_updated(self._panel)
        if self._active_dialog is not None:
            self._active_dialog._update_plot()

    def _on_profile_range_selected(self, lane_idx: int, y_start: float, y_end: float) -> None:
        try:
            band = self._panel.analyzer.add_manual_band_range(lane_idx, y_start, y_end)
        except Exception as e:
            self._panel.status_message.emit(f"Error adding band range: {e}")
            return
        if band:
            self._emit_bands_updated(self._panel)
            if self._active_dialog is not None:
                self._active_dialog._update_plot()

    def _on_profile_band_removed(self, lane_idx: int, y_pos: float) -> None:
        if self._panel.analyzer.remove_band_at(lane_idx, y_pos):
            self._panel.status_message.emit(f"Removed band in lane {lane_idx + 1}")
            self._emit_bands_updated(self._panel)
            if self._active_dialog is not None:
                self._active_dialog._update_plot()

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_lane_types(self) -> dict[int, str]:
        """Pull lane types from WBLanesStep if present, else default all Sample."""
        from biopro.plugins.western_blot.ui.steps.wb_lanes import WBLanesStep
        for step in self._panel._steps:
            if isinstance(step, WBLanesStep):
                return step.get_lane_types()
        return {}