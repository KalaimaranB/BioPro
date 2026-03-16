"""Western Blot — Step 2: Lane Detection."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors
from biopro.ui.wizard.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


class WBLanesStep(WizardStep):
    """Detect lane boundaries in the preprocessed image."""

    label = "Lanes"

    # ── WizardStep interface ──────────────────────────────────────────

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._canvas = None
        self._manually_adjusted = False

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        lane_group = QGroupBox("Lane Detection")
        lane_layout = QVBoxLayout(lane_group)
        lane_layout.setSpacing(8)

        self.chk_auto_lanes = QCheckBox("Auto-detect lanes")
        self.chk_auto_lanes.setChecked(True)
        self.chk_auto_lanes.toggled.connect(self._toggle_manual_lanes)
        lane_layout.addWidget(self.chk_auto_lanes)

        self.spin_lanes = QSpinBox()
        self.spin_lanes.setRange(1, 30)
        self.spin_lanes.setValue(6)
        self.spin_lanes.setToolTip(
            "Override lane count — uncheck auto-detect to use this value.\n"
            "You can also type directly here; auto-detect will be unchecked automatically."
        )
        self.spin_lanes.valueChanged.connect(
            lambda _: self._on_lane_count_manually_changed(panel)
        )
        lane_layout.addLayout(self._row("Number of lanes:", self.spin_lanes))

        self.spin_smoothing = QSpinBox()
        self.spin_smoothing.setRange(3, 51)
        self.spin_smoothing.setValue(15)
        self.spin_smoothing.setSingleStep(2)
        self.spin_smoothing.setToolTip(
            "Smoothing window for the lane detection projection. "
            "Increase for noisy images."
        )
        lane_layout.addLayout(self._row("Smoothing:", self.spin_smoothing))

        self.btn_detect = QPushButton("🔍  Detect Lanes")
        self.btn_detect.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f" border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.ACCENT_PRIMARY_PRESSED}; }}"
            f"QPushButton:disabled {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_DISABLED}; }}"
        )
        self.btn_detect.setMinimumHeight(36)
        self.btn_detect.clicked.connect(lambda: self.run_detection(panel))
        lane_layout.addWidget(self.btn_detect)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitle")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(18)
        lane_layout.addWidget(self.lbl_status)

        layout.addWidget(lane_group)

        # Lane type selectors — populated after detection
        self._lane_type_group = QGroupBox("Lane Types")
        lane_type_layout = QVBoxLayout(self._lane_type_group)
        lane_type_layout.setSpacing(4)

        desc = QLabel("Mark lanes as Ladder or Exclude to skip them in analysis:")
        desc.setWordWrap(True)
        desc.setMinimumHeight(18)
        lane_type_layout.addWidget(desc)

        self._lane_type_container = QVBoxLayout()
        self.lane_type_combos: list[QComboBox] = []
        lane_type_layout.addLayout(self._lane_type_container)

        self.lbl_no_lanes = QLabel("(detect lanes first)")
        self.lbl_no_lanes.setObjectName("subtitle")
        lane_type_layout.addWidget(self.lbl_no_lanes)

        layout.addWidget(self._lane_type_group)
        layout.addStretch()
        return self._scroll(page)

    def on_next(self, panel: WizardPanel) -> bool:
        if self._manually_adjusted and panel.analyzer.state.lanes:
            return True  # keep dragged borders, skip re-detection
        self.run_detection(panel)
        return bool(panel.analyzer.state.lanes)

    # ── Lane detection ────────────────────────────────────────────────

    def _auto_lanes_checked(self) -> bool:
        return self.chk_auto_lanes.isChecked()

    def _on_lane_count_manually_changed(self, panel: WizardPanel) -> None:
        """Uncheck auto and re-run when user types a lane count."""
        self._manually_adjusted = False
        if self.chk_auto_lanes.isChecked():
            self.chk_auto_lanes.blockSignals(True)
            self.chk_auto_lanes.setChecked(False)
            self.chk_auto_lanes.blockSignals(False)
        if panel.analyzer.state.processed_image is not None:
            self.run_detection(panel)

    def run_detection(self, panel: WizardPanel) -> None:
        """Run lane detection and update UI. Called by Next and by WBLoadStep."""
        try:
            num_lanes = None if self.chk_auto_lanes.isChecked() else self.spin_lanes.value()
            lanes = panel.analyzer.detect_lanes(
                num_lanes=num_lanes,
                smoothing_window=self.spin_smoothing.value(),
            )
            # Update spinbox to show detected count but block signal to
            # avoid triggering _on_lane_count_manually_changed in a loop
            self.spin_lanes.blockSignals(True)
            self.spin_lanes.setValue(len(lanes))
            self.spin_lanes.blockSignals(False)

            self.lbl_status.setText(f"✅  Detected {len(lanes)} lanes")
            self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            panel.status_message.emit(f"Detected {len(lanes)} lanes")
            self._populate_lane_type_combos(len(lanes))
            panel.lanes_detected.emit(lanes)
        except Exception as e:
            self.lbl_status.setText(f"❌  {e}")
            self.lbl_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Lane detection error")

    def _toggle_manual_lanes(self, auto: bool) -> None:
        pass  # spinbox always enabled; auto flag controls num_lanes=None

    def _populate_lane_type_combos(self, num_lanes: int) -> None:
        for combo in self.lane_type_combos:
            combo.setParent(None)
            combo.deleteLater()
        self.lane_type_combos.clear()
        self.lbl_no_lanes.setVisible(False)

        while self._lane_type_container.count():
            item = self._lane_type_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i in range(num_lanes):
            row = QHBoxLayout()
            lbl = QLabel(f"Lane {i + 1}:")
            lbl.setFixedWidth(56)
            combo = QComboBox()
            combo.addItems(["Sample", "Ladder", "Exclude"])
            combo.setToolTip(
                "Sample: include in analysis\n"
                "Ladder: molecular weight marker\n"
                "Exclude: skip entirely"
            )
            self.lane_type_combos.append(combo)
            row.addWidget(lbl)
            row.addWidget(combo)
            wrapper = QWidget()
            wrapper.setLayout(row)
            self._lane_type_container.addWidget(wrapper)

    def get_lane_types(self) -> dict[int, str]:
        return {i: combo.currentText() for i, combo in enumerate(self.lane_type_combos)}

    def set_canvas(self, canvas) -> None:
        """Store canvas reference for lane edit mode and border drag signal."""
        self._canvas = canvas

    def on_enter(self) -> None:
        # Sync spinbox to last detected count regardless of auto mode
        lanes = self._panel.analyzer.state.lanes
        if lanes:
            self.spin_lanes.blockSignals(True)
            self.spin_lanes.setValue(len(lanes))
            self.spin_lanes.blockSignals(False)
        # Enable draggable lane borders and connect signal
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.set_lane_edit_mode(True)
            # Reconnect — disconnect first to avoid duplicate connections
            try:
                canvas.lane_border_changed.disconnect(self._on_lane_border_changed)
            except Exception:
                pass
            canvas.lane_border_changed.connect(self._on_lane_border_changed)
            # Redraw lanes with draggable borders
            if self._panel.analyzer.state.lanes:
                canvas.add_lane_overlays(self._panel.analyzer.state.lanes)

    def on_leave(self) -> None:
        """Called when navigating away — disable lane edit mode."""
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.set_lane_edit_mode(False)
            try:
                canvas.lane_border_changed.disconnect(self._on_lane_border_changed)
            except Exception:
                pass
            # Redraw without draggable borders
            if self._panel.analyzer.state.lanes:
                canvas.add_lane_overlays(self._panel.analyzer.state.lanes)

    def _on_lane_border_changed(self, border_idx: int, new_x: float) -> None:
        """Rebuild LaneROI list when user drags a border line."""
        lanes = self._panel.analyzer.state.lanes
        if not lanes:
            return

        # Collect current boundaries [0, x1, x2, ..., w]
        boundaries = [lanes[0].x_start]
        for lane in lanes:
            boundaries.append(lane.x_end)

        # border_idx maps to boundaries[border_idx] (the internal splits)
        if border_idx < 1 or border_idx >= len(boundaries) - 1:
            return

        boundaries[border_idx] = int(round(new_x))
        # Enforce monotonicity — no lane can have zero or negative width
        MIN_WIDTH = 10
        for i in range(1, len(boundaries)):
            if boundaries[i] <= boundaries[i - 1] + MIN_WIDTH:
                boundaries[i] = boundaries[i - 1] + MIN_WIDTH

        from biopro.analysis.lane_detection import LaneROI
        img_h = lanes[0].y_end
        new_lanes = [
            LaneROI(
                index=i,
                x_start=boundaries[i],
                x_end=boundaries[i + 1],
                y_start=0,
                y_end=img_h,
            )
            for i in range(len(boundaries) - 1)
        ]

        # Update analyzer state
        self._panel.analyzer.state.lanes = new_lanes
        self._panel.analyzer.state.profiles = []
        self._panel.analyzer.state.baselines = []
        self._panel.analyzer.state.bands = []
        self._panel.analyzer.state.results_df = None

        # Redraw lane overlays (borders stay draggable)
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.add_lane_overlays(new_lanes)

        self._panel.lanes_detected.emit(new_lanes)
        self._manually_adjusted = True
        self._panel.status_message.emit(
            f"Lane border moved — {len(new_lanes)} lanes. "
            "Proceed to Bands step to re-detect bands."
        )
        self.lbl_status.setText(
            f"✅  {len(new_lanes)} lanes (manually adjusted)"
        )
        self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")