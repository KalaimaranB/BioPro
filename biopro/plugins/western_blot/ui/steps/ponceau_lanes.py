"""Ponceau Stain — Step 2: Lane Detection & Mapping.

Detects lanes in the Ponceau image and lets the user map each Ponceau
lane to its corresponding WB lane.  This handles the case where the two
images have different numbers of lanes (e.g. extra ladder lane on one).
"""

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

from biopro.plugins.western_blot.ui.base import WizardPanel, WizardStep
from biopro.plugins.western_blot.ui.steps.base_step import BaseStepWidget

from biopro.ui.theme import Colors
from biopro.plugins.western_blot.ui.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


class PonceauLanesStep(WizardStep):
    """Detect Ponceau lanes and map them to WB lanes."""

    label = "Pon. Lanes"

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._canvas = None
        self._manually_adjusted = False
        self._wb_lane_count = 0

        # 1. Use the new Base Class!
        page = BaseStepWidget(
            title="Step 2: Ponceau Lanes",
            subtitle="Detect Ponceau lanes and map them to the Western Blot lanes."
        )

        # 2. Lane detection group
        lane_group = QGroupBox("Ponceau Lane Detection")
        lane_layout = QVBoxLayout(lane_group)
        lane_layout.setSpacing(8)

        self.chk_auto = QCheckBox("Auto-detect lanes")
        self.chk_auto.setChecked(True)
        lane_layout.addWidget(self.chk_auto)

        self.spin_lanes = QSpinBox()
        self.spin_lanes.setRange(1, 30)
        self.spin_lanes.setValue(6)
        self.spin_lanes.valueChanged.connect(lambda _: self._on_lane_count_manually_changed(panel))
        lane_layout.addLayout(self._row("Number of lanes:", self.spin_lanes))

        self.spin_smoothing = QSpinBox()
        self.spin_smoothing.setRange(3, 51)
        self.spin_smoothing.setValue(15)
        self.spin_smoothing.setSingleStep(2)
        lane_layout.addLayout(self._row("Smoothing:", self.spin_smoothing))

        self.btn_detect = QPushButton("🔍  Detect Ponceau Lanes")
        self.btn_detect.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f" border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
        )
        self.btn_detect.setMinimumHeight(36)
        self.btn_detect.clicked.connect(lambda: self._detect_lanes(panel))
        lane_layout.addWidget(self.btn_detect)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitle")
        lane_layout.addWidget(self.lbl_status)

        page.add_content_widget(lane_group) # <-- Add it to the base class!

        # 3. Lane count warning
        self.lbl_mismatch = QLabel("")
        self.lbl_mismatch.setWordWrap(True)
        page.add_content_widget(self.lbl_mismatch) # <-- Add it to the base class!

        # 4. Lane mapping
        self._mapping_group = QGroupBox("Lane Mapping  —  Ponceau lane → WB lane")
        mapping_top = QVBoxLayout(self._mapping_group)
        
        map_hint = QLabel("Select the corresponding WB lane for each Ponceau lane.")
        map_hint.setWordWrap(True)
        map_hint.setObjectName("subtitle")
        mapping_top.addWidget(map_hint)

        self._mapping_container = QVBoxLayout()
        mapping_top.addLayout(self._mapping_container)
        self._mapping_combos: list[QComboBox] = []

        self.lbl_no_lanes = QLabel("(detect lanes first)")
        self.lbl_no_lanes.setObjectName("subtitle")
        mapping_top.addWidget(self.lbl_no_lanes)

        page.add_content_widget(self._mapping_group) # <-- Add it to the base class!

        return self._scroll(page)
    
    def set_canvas(self, canvas) -> None:
        self._canvas = canvas

    def on_enter(self) -> None:
        """Refresh WB lane count when we arrive at this step."""
        from biopro.plugins.western_blot.ui.steps.wb_lanes import WBLanesStep
        for step in self._panel._steps:
            if isinstance(step, WBLanesStep):
                self._wb_lane_count = len(self._panel.analyzer.state.lanes)
                break
        # Sync spinbox to last detected count regardless of auto mode
        pon_lanes = self._panel.ponceau_analyzer.state.lanes
        if pon_lanes:
            self.spin_lanes.blockSignals(True)
            self.spin_lanes.setValue(len(pon_lanes))
            self.spin_lanes.blockSignals(False)
            self._rebuild_mapping(len(pon_lanes))
        # Enable draggable lane borders
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.set_lane_edit_mode(True)
            try:
                canvas.lane_border_changed.disconnect(self._on_lane_border_changed)
            except Exception:
                pass
            canvas.lane_border_changed.connect(self._on_lane_border_changed)
            if pon_lanes:
                canvas.add_lane_overlays(pon_lanes)

    def on_leave(self) -> None:
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.set_lane_edit_mode(False)
            try:
                canvas.lane_border_changed.disconnect(self._on_lane_border_changed)
            except Exception:
                pass
            if self._panel.ponceau_analyzer.state.lanes:
                canvas.add_lane_overlays(self._panel.ponceau_analyzer.state.lanes)

    def on_next(self, panel: WizardPanel) -> bool:
        if self._manually_adjusted and panel.ponceau_analyzer.state.lanes:
            # User dragged borders — keep their adjustments, skip re-detection
            self._save_mapping(panel)
            return True
        # Otherwise re-run so parameter changes take effect
        self._detect_lanes(panel)
        if not panel.ponceau_analyzer.state.lanes:
            return False
        self._save_mapping(panel)
        return True

    # ── Lane detection ────────────────────────────────────────────────

    def _on_lane_border_changed(self, border_idx: int, new_x: float) -> None:
        """Rebuild Ponceau LaneROI list when user drags a border."""
        lanes = self._panel.ponceau_analyzer.state.lanes
        if not lanes:
            return
        boundaries = [lanes[0].x_start]
        for lane in lanes:
            boundaries.append(lane.x_end)
        if border_idx < 1 or border_idx >= len(boundaries) - 1:
            return
        boundaries[border_idx] = int(round(new_x))
        MIN_WIDTH = 10
        for i in range(1, len(boundaries)):
            if boundaries[i] <= boundaries[i - 1] + MIN_WIDTH:
                boundaries[i] = boundaries[i - 1] + MIN_WIDTH
        from biopro.plugins.western_blot.analysis.lane_detection import LaneROI
        img_h = lanes[0].y_end
        new_lanes = [
            LaneROI(index=i, x_start=boundaries[i], x_end=boundaries[i+1],
                    y_start=0, y_end=img_h)
            for i in range(len(boundaries) - 1)
        ]
        self._panel.ponceau_analyzer.state.lanes = new_lanes
        self._panel.ponceau_analyzer.state.profiles = []
        self._panel.ponceau_analyzer.state.baselines = []
        self._panel.ponceau_analyzer.state.bands = []
        canvas = getattr(self, "_canvas", None)
        if canvas is not None:
            canvas.add_lane_overlays(new_lanes)
        self._panel.lanes_detected.emit(new_lanes)
        self._check_lane_count_match(len(new_lanes))
        self._rebuild_mapping(len(new_lanes))
        self._manually_adjusted = True
        self.lbl_status.setText(f"✅  {len(new_lanes)} lanes (manually adjusted)")
        self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")

    def _on_lane_count_manually_changed(self, panel: WizardPanel) -> None:
        """Uncheck auto and re-run detection when user edits spinbox."""
        self._manually_adjusted = False  # User wants fresh detection
        if self.chk_auto.isChecked():
            self.chk_auto.blockSignals(True)
            self.chk_auto.setChecked(False)
            self.chk_auto.blockSignals(False)
        if panel.ponceau_analyzer.state.processed_image is not None:
            self._detect_lanes(panel)

    def _detect_lanes(self, panel: WizardPanel) -> None:
        try:
            num_lanes = None if self.chk_auto.isChecked() else self.spin_lanes.value()
            lanes = panel.ponceau_analyzer.detect_lanes(
                num_lanes=num_lanes,
                smoothing_window=self.spin_smoothing.value(),
            )
            # Always update spinbox with detected count, blocking signal
            # to avoid triggering _on_lane_count_manually_changed in a loop
            self.spin_lanes.blockSignals(True)
            self.spin_lanes.setValue(len(lanes))
            self.spin_lanes.blockSignals(False)

            self.lbl_status.setText(f"✅  Detected {len(lanes)} Ponceau lanes")
            self.lbl_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            panel.status_message.emit(f"Ponceau: {len(lanes)} lanes detected")
            panel.lanes_detected.emit(lanes)

            self._check_lane_count_match(len(lanes))
            self._rebuild_mapping(len(lanes))
            # Redraw with draggable borders if edit mode is active
            canvas = getattr(self, "_canvas", None)
            if canvas is not None and canvas._lane_edit_mode:
                canvas.add_lane_overlays(lanes)

        except Exception as e:
            self.lbl_status.setText(f"❌  {e}")
            self.lbl_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Ponceau lane detection error")

    def _check_lane_count_match(self, pon_count: int) -> None:
        """Show a warning if Ponceau and WB lane counts differ."""
        wb_count = self._wb_lane_count
        if wb_count == 0:
            self.lbl_mismatch.setText("")
            return
        if pon_count == wb_count:
            self.lbl_mismatch.setText(
                f"✅  Ponceau lanes ({pon_count}) match WB lanes ({wb_count})."
            )
            self.lbl_mismatch.setStyleSheet(f"color: {Colors.SUCCESS};")
        else:
            self.lbl_mismatch.setText(
                f"⚠️  Ponceau has {pon_count} lanes but WB has {wb_count} lanes.\n"
                f"Use the mapping below to assign which Ponceau lane corresponds "
                f"to each WB lane.  Set extras to 'Skip'."
            )
            self.lbl_mismatch.setStyleSheet(f"color: {Colors.ACCENT_WARNING};")

    # ── Mapping UI ────────────────────────────────────────────────────

    def _rebuild_mapping(self, pon_lane_count: int) -> None:
        """Rebuild the lane mapping combo boxes."""
        # Clear existing
        for combo in self._mapping_combos:
            combo.setParent(None)
            combo.deleteLater()
        self._mapping_combos.clear()
        while self._mapping_container.count():
            item = self._mapping_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.lbl_no_lanes.setVisible(False)
        wb_count = max(self._wb_lane_count, pon_lane_count)

        for pon_idx in range(pon_lane_count):
            row = QHBoxLayout()
            lbl = QLabel(f"Ponceau lane {pon_idx + 1}  →")
            lbl.setFixedWidth(130)
            combo = QComboBox()
            combo.addItem("Skip (no WB match)")
            for wb_idx in range(wb_count):
                combo.addItem(f"WB lane {wb_idx + 1}")
            # Default: assume 1:1 correspondence up to wb_count
            default = pon_idx if pon_idx < wb_count else 0  # 0 = Skip
            combo.setCurrentIndex(pon_idx + 1 if pon_idx < wb_count else 0)
            self._mapping_combos.append(combo)
            row.addWidget(lbl)
            row.addWidget(combo)
            wrapper = QWidget()
            wrapper.setLayout(row)
            self._mapping_container.addWidget(wrapper)

    def _save_mapping(self, panel: WizardPanel) -> None:
        """Read combos and write to PonceauAnalyzer.lane_mapping."""
        mapping: dict[int, int] = {}
        for pon_idx, combo in enumerate(self._mapping_combos):
            ci = combo.currentIndex()
            if ci == 0:
                continue  # Skip
            wb_idx = ci - 1  # 0-indexed WB lane
            mapping[pon_idx] = wb_idx
        panel.ponceau_analyzer.lane_mapping = mapping
        logger.info("Ponceau lane mapping: %s", mapping)