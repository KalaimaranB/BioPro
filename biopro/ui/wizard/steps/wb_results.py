"""Western Blot — Step 4: Results & Normalization."""

from __future__ import annotations

import logging

import pandas as pd

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors
from biopro.ui.wizard.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


class WBResultsStep(WizardStep):
    """Compute densitometry, apply normalization, emit results."""

    label = "Results"
    is_terminal = True

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # ── WB internal normalization ─────────────────────────────────
        norm_group = QGroupBox("WB Normalization")
        norm_layout = QVBoxLayout(norm_group)
        norm_layout.setSpacing(8)

        self.combo_ref_lane = QComboBox()
        self.combo_ref_lane.addItem("None (% of total)")
        self.combo_ref_lane.setToolTip(
            "Optionally pick a WB reference lane for band-based normalisation.\n"
            "Usually left as 'None' when Ponceau normalisation is used."
        )
        self.combo_ref_lane.currentIndexChanged.connect(lambda _: self._compute_results())
        norm_layout.addLayout(self._row("Reference lane:", self.combo_ref_lane))

        self.chk_normalize_one = QCheckBox("Set control lane to 1.0")
        self.chk_normalize_one.setChecked(True)
        self.chk_normalize_one.toggled.connect(lambda _: self._compute_results())
        norm_layout.addWidget(self.chk_normalize_one)

        layout.addWidget(norm_group)

        # ── Ponceau status ────────────────────────────────────────────
        self._ponceau_group = QGroupBox("Ponceau Loading Normalisation")
        pon_layout = QVBoxLayout(self._ponceau_group)
        pon_layout.setSpacing(6)

        self.lbl_ponceau_status = QLabel("No Ponceau data — results will not be loading-corrected.")
        self.lbl_ponceau_status.setWordWrap(True)
        self.lbl_ponceau_status.setObjectName("subtitle")
        pon_layout.addWidget(self.lbl_ponceau_status)

        self.chk_use_ponceau = QCheckBox("Apply Ponceau loading correction")
        self.chk_use_ponceau.setChecked(True)
        self.chk_use_ponceau.setVisible(False)
        self.chk_use_ponceau.toggled.connect(lambda _: self._compute_results())
        pon_layout.addWidget(self.chk_use_ponceau)

        layout.addWidget(self._ponceau_group)

        info = QLabel("Results update automatically in the right panel.")
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        info.setMinimumHeight(32)
        layout.addWidget(info)

        layout.addStretch()
        return self._scroll(page)

    def on_enter(self) -> None:
        """Refresh Ponceau status and auto-compute when entering."""
        self._refresh_ponceau_status()
        self._compute_results()

    def on_next(self, panel: WizardPanel) -> bool:
        return False  # terminal

    def on_band_clicked(self, band, panel: WizardPanel) -> None:
        """Route canvas band clicks to the results widget slot selector."""
        rw = getattr(panel, "_results_widget_ref", None)
        if rw is not None and hasattr(rw, "assign_band_to_active_slot"):
            rw.assign_band_to_active_slot(band)
        panel.status_message.emit(
            f"Band assigned — Lane {band.lane_index+1}, "
            f"pos {band.position}px, SNR {band.snr:.1f}"
        )
        # Recompute immediately when a band is assigned
        self._compute_results()

    # ── Public ────────────────────────────────────────────────────────

    def update_ref_lane_combo(self, num_lanes: int) -> None:
        self.combo_ref_lane.blockSignals(True)
        self.combo_ref_lane.clear()
        self.combo_ref_lane.addItem("None (% of total)")
        for i in range(num_lanes):
            self.combo_ref_lane.addItem(f"Lane {i + 1}")
        self.combo_ref_lane.blockSignals(False)

    # ── Internal ──────────────────────────────────────────────────────

    def _refresh_ponceau_status(self) -> None:
        """Update the Ponceau status label based on available data."""
        ponceau = getattr(self._panel, "ponceau_analyzer", None)
        has_ponceau = (
            ponceau is not None
            and ponceau.state.bands
            and ponceau.lane_mapping
        )
        if has_ponceau:
            nb_mapped = len(ponceau.lane_mapping)
            mode = ponceau.mode.replace("_", " ")
            self.lbl_ponceau_status.setText(
                f"✅  Ponceau data available — {nb_mapped} lanes mapped "
                f"(mode: {mode}).\n"
                f"Loading factors will be applied to produce 'Ponceau Normalised' values."
            )
            self.lbl_ponceau_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.chk_use_ponceau.setVisible(True)
        else:
            self.lbl_ponceau_status.setText(
                "No Ponceau data — results will show WB-only normalisation.\n"
                "Go back to complete the Ponceau stage to enable loading correction."
            )
            self.lbl_ponceau_status.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
            self.chk_use_ponceau.setVisible(False)

    def _compute_results(self) -> None:
        """Compute results using the professor's intra-lane normalisation method.

        For each lane::

            ratio = WB_band_intensity / Ponceau_ref_band_intensity

        The WB band is whatever the user selected in the results comparison
        slots (stored on the ResultsWidget).  If no band is selected for a
        lane, the highest-intensity band in that lane is used as a default.

        The ratios are optionally scaled so the first (control) lane = 1.0.
        """
        try:
            lane_types = self._get_lane_types()
            nb_wb = len(self._panel.analyzer.state.lanes)

            # ── Step 1: get WB band intensity per lane ─────────────────
            rw = getattr(self._panel, "_results_widget_ref", None)
            selected_bands: dict[int, object] = {}  # wb_lane_idx → DetectedBand
            if rw is not None and hasattr(rw, "_slots"):
                for band in rw._slots:
                    if band is not None:
                        selected_bands[band.lane_index] = band

            all_wb_bands = [
                b for b in self._panel.analyzer.state.bands
                if getattr(b, "selected", True)
                and lane_types.get(b.lane_index, "Sample") not in ("Exclude",)
            ]
            wb_intensity: dict[int, float] = {}
            wb_band_pos: dict[int, int] = {}
            for lane_idx in range(nb_wb):
                lt = lane_types.get(lane_idx, "Sample")
                if lt == "Exclude":
                    continue
                if lane_idx in selected_bands:
                    b = selected_bands[lane_idx]
                    intensity = float(b.integrated_intensity)
                    if intensity < 1e-6:
                        intensity = float(b.peak_height)
                        logger.warning(
                            "Lane %d: integrated_intensity=0, using peak_height=%.4f",
                            lane_idx, intensity,
                        )
                    wb_intensity[lane_idx] = intensity
                    wb_band_pos[lane_idx] = int(b.position)
                else:
                    lane_bands = [b for b in all_wb_bands if b.lane_index == lane_idx]
                    if lane_bands:
                        def _band_score(b):
                            return b.integrated_intensity if b.integrated_intensity > 1e-6 else b.peak_height
                        best = max(lane_bands, key=_band_score)
                        intensity = float(best.integrated_intensity)
                        if intensity < 1e-6:
                            intensity = float(best.peak_height)
                        wb_intensity[lane_idx] = intensity
                        wb_band_pos[lane_idx] = int(best.position)

            # ── Step 2: get Ponceau raw intensity per WB lane ──────────
            ponceau = getattr(self._panel, "ponceau_analyzer", None)
            use_ponceau = (
                self.chk_use_ponceau.isChecked()
                and self.chk_use_ponceau.isVisible()
                and ponceau is not None
                and ponceau.state.bands
                and ponceau.lane_mapping
            )

            ponceau_raw: dict[int, float] = {}
            if use_ponceau:
                ponceau_raw = ponceau.get_ponceau_raw_per_wb_lane(nb_wb)

            # ── Step 3: compute per-lane ratio ─────────────────────────
            records = []
            for lane_idx in sorted(wb_intensity.keys()):
                wb_raw = wb_intensity[lane_idx]
                pon_raw = ponceau_raw.get(lane_idx, 0.0)

                if use_ponceau and pon_raw > 0:
                    ratio = wb_raw / pon_raw
                else:
                    total = sum(wb_intensity.values()) or 1.0
                    ratio = wb_raw / total

                records.append({
                    "lane": lane_idx,
                    "wb_band_position": wb_band_pos.get(lane_idx, 0),
                    "wb_raw": round(wb_raw, 4),
                    "ponceau_raw": round(pon_raw, 4) if use_ponceau else None,
                    "ratio": round(ratio, 6),
                    "normalised_ratio": ratio,  # scaled below
                    "is_ladder": lane_types.get(lane_idx, "Sample") == "Ladder",
                })

            df = pd.DataFrame(records)

            # ── Step 4: optionally scale control lane to 1.0 ──────────
            if self.chk_normalize_one.isChecked() and not df.empty:
                sample_rows = df[~df["is_ladder"]]
                if not sample_rows.empty:
                    ref_idx = self.combo_ref_lane.currentIndex()
                    if ref_idx > 0:
                        ctrl_lane = ref_idx - 1
                    else:
                        ctrl_lane = int(sample_rows.iloc[0]["lane"])
                    ctrl_rows = df[df["lane"] == ctrl_lane]
                    if not ctrl_rows.empty:
                        ctrl_ratio = float(ctrl_rows.iloc[0]["ratio"])
                        if ctrl_ratio > 0:
                            df["normalised_ratio"] = df["ratio"] / ctrl_ratio

            df["normalised_ratio"] = df["normalised_ratio"].round(4)

            self._panel.status_message.emit(
                f"Results computed: {len(df)} lanes analysed"
                + (" (Ponceau-normalised)" if use_ponceau else "")
            )
            self._panel.results_ready.emit(df)

        except Exception as e:
            self._panel.status_message.emit(f"Error computing results: {e}")
            logger.exception("Densitometry error")

    def _get_lane_types(self) -> dict[int, str]:
        from biopro.ui.wizard.steps.wb_lanes import WBLanesStep
        for step in self._panel._steps:
            if isinstance(step, WBLanesStep):
                return step.get_lane_types()
        return {}