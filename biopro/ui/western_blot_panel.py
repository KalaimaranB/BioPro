"""Western blot analysis wizard panel.

A guided, step-by-step panel that replaces the 20-step ImageJ workflow
with a clean 4-step wizard:

    1. **Load & Preprocess** — Open image, toggle inversion, adjust rotation.
    2. **Lane Setup** — Auto-detect or specify lane count.
    3. **Band Detection** — Adjust sensitivity, preview peaks.
    4. **Results** — View chart, export data.

Each step emits signals to update the main window's image canvas
and results display.

Design Notes:
    - The panel is a QWidget with a QStackedWidget for step pages.
    - A progress indicator at the top shows the current step.
    - "Back" and "Next" buttons navigate between steps.
    - All analysis is performed via ``WesternBlotAnalyzer`` — the panel
      never touches raw image arrays directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsOpacityEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QScrollArea,
    QWidget,
)

from PyQt6.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve

from biopro.analysis.western_blot import WesternBlotAnalyzer
from biopro.ui.theme import Colors
from biopro.ui.lane_profile_dialog import LaneProfileDialog

logger = logging.getLogger(__name__)


class StepIndicator(QWidget):
    """Visual step progress indicator.

    Displays a horizontal row of dots/labels showing the current
    step in the wizard.
    """

    STEPS = ["Load & Preprocess", "Lane Setup", "Band Detection", "Results"]

    def __init__(self, parent=None) -> None:
        """Initialize the step indicator."""
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._labels: list[QLabel] = []
        for i, step_name in enumerate(self.STEPS):
            # Step dot + label
            lbl = QLabel(f"  {i + 1}. {step_name}")
            lbl.setObjectName("subtitle")
            self._labels.append(lbl)
            layout.addWidget(lbl)

            if i < len(self.STEPS) - 1:
                separator = QLabel("  →  ")
                separator.setObjectName("subtitle")
                layout.addWidget(separator)

        layout.addStretch()
        self.set_current_step(0)

    def set_current_step(self, step: int) -> None:
        """Highlight the current step.

        Args:
            step: Zero-based step index.
        """
        for i, lbl in enumerate(self._labels):
            if i == step:
                lbl.setStyleSheet(
                    f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold;"
                )
            elif i < step:
                lbl.setStyleSheet(f"color: {Colors.SUCCESS};")
            else:
                lbl.setStyleSheet(f"color: {Colors.FG_SECONDARY};")


class FadingStackedWidget(QStackedWidget):
    """A QStackedWidget with a smooth cross-fade transition."""

    def __init__(self, parent=None, fade_ms: int = 300) -> None:
        super().__init__(parent)
        self.fade_ms = fade_ms

    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex():
            return

        current_widget = self.currentWidget()
        next_widget = self.widget(index)

        if current_widget is None or next_widget is None:
            super().setCurrentIndex(index)
            return

        # Prepare next widget with 0 opacity
        effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        
        super().setCurrentIndex(index)

        # Animate opacity to 1.0
        self.anim = QPropertyAnimation(effect, b"opacity")
        self.anim.setDuration(self.fade_ms)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Remove the effect after animation so it doesn't interfere with rendering later
        self.anim.finished.connect(lambda: next_widget.setGraphicsEffect(None))
        self.anim.start()


class WesternBlotPanel(QWidget):
    """Wizard-style panel for western blot analysis.

    Signals:
        image_changed: Emitted when the image is loaded or preprocessed.
            Payload: the processed image as a numpy array.
        lanes_detected: Emitted when lanes are detected.
            Payload: list of LaneROI objects.
        bands_detected: Emitted when bands are detected.
            Payload: (list of DetectedBand, list of LaneROI).
        results_ready: Emitted when results are computed.
            Payload: pandas DataFrame.
        status_message: Emitted to display a status bar message.
    """

    image_changed = pyqtSignal(object)        # NDArray
    lanes_detected = pyqtSignal(object)       # list[LaneROI]
    bands_detected = pyqtSignal(object, object)  # bands, lanes
    results_ready = pyqtSignal(object)        # pd.DataFrame
    status_message = pyqtSignal(str)
    selected_bands_changed = pyqtSignal(list)
    peak_picking_enabled = pyqtSignal(bool)
    crop_mode_toggled = pyqtSignal(bool)
    profile_hovered = pyqtSignal(int, float)  # lane_index, y_pos (profile coords)

    def __init__(self, parent=None) -> None:
        """Initialize the wizard panel."""
        super().__init__(parent)

        self.analyzer = WesternBlotAnalyzer()
        self._current_step = 0
        self._manual_peak_picking = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the wizard layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("🧬 Western Blot Analysis")
        title.setObjectName("stepTitle")
        layout.addWidget(title)

        # Step indicator
        self.step_indicator = StepIndicator()
        layout.addWidget(self.step_indicator)

        # Stacked pages (one per step)
        self.pages = FadingStackedWidget(fade_ms=350)
        self.pages.addWidget(self._create_step1_load())
        self.pages.addWidget(self._create_step2_lanes())
        self.pages.addWidget(self._create_step3_bands())
        self.pages.addWidget(self._create_step4_results())
        layout.addWidget(self.pages, stretch=1)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("← Back")
        self.btn_next = QPushButton("Next →")
        self.btn_next.setObjectName("primaryButton")

        self.btn_back.clicked.connect(self._go_back)
        self.btn_next.clicked.connect(self._go_next)

        nav_layout.addWidget(self.btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)

        # Initial state
        self._update_nav_buttons()

    # ── Step 1: Load & Preprocess ────────────────────────────────────

    def _create_step1_load(self) -> QWidget:
        """Create the load & preprocess page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # File picker
        file_group = QGroupBox("Image File")
        file_layout = QVBoxLayout(file_group)

        self.btn_open = QPushButton("📁  Open Image File...")
        self.btn_open.setMinimumHeight(40)
        self.btn_open.clicked.connect(self._open_file)
        file_layout.addWidget(self.btn_open)

        self.lbl_filename = QLabel("No file loaded")
        self.lbl_filename.setObjectName("subtitle")
        self.lbl_filename.setWordWrap(True)
        file_layout.addWidget(self.lbl_filename)

        layout.addWidget(file_group)

        # Preprocessing options
        preproc_group = QGroupBox("Preprocessing")
        preproc_layout = QVBoxLayout(preproc_group)

        # Invert LUT
        self.chk_invert = QCheckBox("Auto-detect LUT inversion")
        self.chk_invert.setChecked(True)
        self.chk_invert.setToolTip(
            "Automatically detect if the image needs inversion "
            "so that bands become peaks for detection "
            "(common dark-on-light blots will be inverted)."
        )
        self.chk_invert.toggled.connect(self._on_preprocess_changed)
        preproc_layout.addWidget(self.chk_invert)

        # Rotation
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Rotation:"))
        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-180, 180)
        self.spin_rotation.setValue(0)
        self.spin_rotation.setSuffix("°")
        self.spin_rotation.setSingleStep(0.5)
        self.spin_rotation.setToolTip(
            "Rotate the image to straighten bands. "
            "Positive = counter-clockwise."
        )
        self.spin_rotation.valueChanged.connect(self._on_rotation_changed)
        rot_layout.addWidget(self.spin_rotation)
        preproc_layout.addLayout(rot_layout)
        
        # Contrast
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Contrast:"))
        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.1, 5.0)
        self.spin_contrast.setValue(1.0)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setToolTip(
            "Adjust image contrast. >1.0 increases contrast, <1.0 decreases contrast."
        )
        self.spin_contrast.valueChanged.connect(self._on_preprocess_changed)
        contrast_layout.addWidget(self.spin_contrast)
        preproc_layout.addLayout(contrast_layout)
        
        # Manual Crop Toggle
        self.btn_manual_crop = QPushButton("✂️  Manual Crop")
        self.btn_manual_crop.setCheckable(True)
        self.btn_manual_crop.setToolTip("Draw a rectangle on the image to crop it. \nAutomatically applied. Cleared if you rotate the image.")
        self.btn_manual_crop.toggled.connect(self._on_manual_crop_toggled)
        preproc_layout.addWidget(self.btn_manual_crop)

        # Auto-crop
        self.chk_autocrop = QCheckBox("Auto-crop borders")
        self.chk_autocrop.setChecked(False)
        self.chk_autocrop.toggled.connect(self._on_preprocess_changed)
        preproc_layout.addWidget(self.chk_autocrop)

        # Apply button (for explicit re-preprocessing)
        self.btn_apply_preprocess = QPushButton("🔄  Apply Preprocessing")
        self.btn_apply_preprocess.setObjectName("primaryButton")
        self.btn_apply_preprocess.setMinimumHeight(36)
        self.btn_apply_preprocess.clicked.connect(self._on_preprocess_changed)
        preproc_layout.addWidget(self.btn_apply_preprocess)

        layout.addWidget(preproc_group)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    # ── Step 2: Lane Setup ───────────────────────────────────────────

    def _create_step2_lanes(self) -> QWidget:
        """Create the lane detection page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        lane_group = QGroupBox("Lane Detection")
        lane_layout = QVBoxLayout(lane_group)

        # Auto-detect toggle
        self.chk_auto_lanes = QCheckBox("Auto-detect lanes")
        self.chk_auto_lanes.setChecked(True)
        self.chk_auto_lanes.toggled.connect(self._toggle_manual_lanes)
        lane_layout.addWidget(self.chk_auto_lanes)

        # Manual lane count
        manual_layout = QHBoxLayout()
        self.lbl_lane_count = QLabel("Number of lanes:")
        self.spin_lanes = QSpinBox()
        self.spin_lanes.setRange(1, 30)
        self.spin_lanes.setValue(6)
        self.spin_lanes.setEnabled(False)  # Disabled when auto is on
        manual_layout.addWidget(self.lbl_lane_count)
        manual_layout.addWidget(self.spin_lanes)
        lane_layout.addLayout(manual_layout)

        # Smoothing control
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(QLabel("Smoothing:"))
        self.spin_smoothing = QSpinBox()
        self.spin_smoothing.setRange(3, 51)
        self.spin_smoothing.setValue(15)
        self.spin_smoothing.setSingleStep(2)
        self.spin_smoothing.setToolTip(
            "Smoothing window for the lane detection projection. "
            "Increase for noisy images."
        )
        smooth_layout.addWidget(self.spin_smoothing)
        lane_layout.addLayout(smooth_layout)

        # Detect button
        self.btn_detect_lanes = QPushButton("🔍  Detect Lanes")
        self.btn_detect_lanes.setObjectName("primaryButton")
        self.btn_detect_lanes.setMinimumHeight(36)
        self.btn_detect_lanes.clicked.connect(self._detect_lanes)
        lane_layout.addWidget(self.btn_detect_lanes)

        # Status
        self.lbl_lane_status = QLabel("")
        self.lbl_lane_status.setObjectName("subtitle")
        self.lbl_lane_status.setWordWrap(True)
        lane_layout.addWidget(self.lbl_lane_status)

        layout.addWidget(lane_group)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    # ── Step 3: Band Detection ───────────────────────────────────────

    def _create_step3_bands(self) -> QWidget:
        """Create the band detection page with improved controls."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        # ─── Detection Parameters ───
        band_group = QGroupBox("Detection Parameters")
        band_layout = QVBoxLayout(band_group)

        # SNR threshold (the most important control)
        snr_layout = QHBoxLayout()
        snr_layout.addWidget(QLabel("Min SNR:"))
        self.spin_snr = QDoubleSpinBox()
        self.spin_snr.setRange(1.0, 20.0)
        self.spin_snr.setValue(3.0)
        self.spin_snr.setSingleStep(0.5)
        self.spin_snr.setToolTip(
            "Signal-to-noise ratio threshold. Higher = fewer false "
            "positives (stricter). Lower = detects weaker bands.\n"
            "• 2.0 = lenient (detect faint bands)\n"
            "• 3.0 = default (good balance)\n"
            "• 5.0 = strict (only strong bands)"
        )
        snr_layout.addWidget(self.spin_snr)
        band_layout.addLayout(snr_layout)

        # Min peak distance
        dist_layout = QHBoxLayout()
        dist_layout.addWidget(QLabel("Min band spacing:"))
        self.spin_peak_distance = QSpinBox()
        self.spin_peak_distance.setRange(3, 100)
        self.spin_peak_distance.setValue(10)
        self.spin_peak_distance.setSuffix(" px")
        self.spin_peak_distance.setToolTip(
            "Minimum distance between adjacent bands in pixels."
        )
        dist_layout.addWidget(self.spin_peak_distance)
        band_layout.addLayout(dist_layout)

        # Max band width
        maxw_layout = QHBoxLayout()
        maxw_layout.addWidget(QLabel("Max band width:"))
        self.spin_max_width = QSpinBox()
        self.spin_max_width.setRange(5, 500)
        self.spin_max_width.setValue(80)
        self.spin_max_width.setSuffix(" px")
        self.spin_max_width.setToolTip(
            "Maximum allowed band width. Peaks wider than this are "
            "rejected (they're likely background artifacts, not real bands)."
        )
        maxw_layout.addWidget(self.spin_max_width)
        band_layout.addLayout(maxw_layout)

        # Min band width
        minw_layout = QHBoxLayout()
        minw_layout.addWidget(QLabel("Min band width:"))
        self.spin_min_width = QSpinBox()
        self.spin_min_width.setRange(1, 50)
        self.spin_min_width.setValue(3)
        self.spin_min_width.setSuffix(" px")
        self.spin_min_width.setToolTip(
            "Minimum band width. Peaks narrower than this are "
            "rejected (they're likely noise spikes)."
        )
        minw_layout.addWidget(self.spin_min_width)
        band_layout.addLayout(minw_layout)

        # Edge margin
        edge_layout = QHBoxLayout()
        edge_layout.addWidget(QLabel("Edge margin:"))
        self.spin_edge_margin = QDoubleSpinBox()
        self.spin_edge_margin.setRange(0.0, 25.0)
        self.spin_edge_margin.setValue(5.0)
        self.spin_edge_margin.setSuffix(" %")
        self.spin_edge_margin.setToolTip(
            "Percentage of lane height at top and bottom to ignore. "
            "Helps avoid false peaks from image boundaries/rotation artifacts."
        )
        edge_layout.addWidget(self.spin_edge_margin)
        band_layout.addLayout(edge_layout)

        layout.addWidget(band_group)

        # ─── Baseline Settings ───
        baseline_group = QGroupBox("Baseline Estimation")
        baseline_layout = QVBoxLayout(baseline_group)

        # Baseline method
        base_layout = QHBoxLayout()
        base_layout.addWidget(QLabel("Method:"))
        self.combo_baseline = QComboBox()
        self.combo_baseline.addItems(["Rolling Ball", "Linear"])
        self.combo_baseline.setToolTip(
            "Rolling Ball: smooth background subtraction (recommended).\n"
            "Linear: straight-line baseline between peak valleys."
        )
        base_layout.addWidget(self.combo_baseline)
        baseline_layout.addLayout(base_layout)

        # Rolling ball radius
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Radius:"))
        self.spin_radius = QSpinBox()
        self.spin_radius.setRange(10, 200)
        self.spin_radius.setValue(50)
        self.spin_radius.setSuffix(" px")
        self.spin_radius.setToolTip(
            "Rolling ball radius. Should be larger than the widest "
            "expected band. Increase for broad, diffuse bands."
        )
        radius_layout.addWidget(self.spin_radius)
        baseline_layout.addLayout(radius_layout)

        layout.addWidget(baseline_group)

        # ─── Lane Type Configuration ───
        lane_type_group = QGroupBox("Lane Types")
        lane_type_layout = QVBoxLayout(lane_type_group)

        desc_label = QLabel("Mark lanes as Ladder or Exclude to skip them in analysis:")
        desc_label.setWordWrap(True)
        lane_type_layout.addWidget(desc_label)

        # Lane type selector (populated dynamically when lanes detected)
        self.lane_type_container = QVBoxLayout()
        self.lane_type_combos: list[QComboBox] = []
        lane_type_layout.addLayout(self.lane_type_container)

        self.lbl_no_lanes_yet = QLabel("(detect lanes first)")
        self.lbl_no_lanes_yet.setObjectName("subtitle")
        self.lbl_no_lanes_yet.setWordWrap(True)
        lane_type_layout.addWidget(self.lbl_no_lanes_yet)

        layout.addWidget(lane_type_group)

        # ─── ImageJ-style manual peak picking ───
        manual_group = QGroupBox("ImageJ-style Peak Picking")
        manual_layout = QVBoxLayout(manual_group)

        self.chk_manual_pick = QCheckBox(
            "Manual peak picking (avoid bad auto-detection on messy blots)"
        )
        self.chk_manual_pick.setChecked(False)
        self.chk_manual_pick.setToolTip(
            "Compute lane profiles/baselines, then click on bands to quantify them.\n"
            "This mirrors ImageJ's gel workflow (plot lanes → close baseline → wand peaks)."
        )
        self.chk_manual_pick.toggled.connect(self._on_manual_pick_toggled)
        manual_layout.addWidget(self.chk_manual_pick)

        hint = QLabel(
            "Workflow: enable manual mode → click 'Detect Bands' (profiles only) → click on bands in the image."
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        manual_layout.addWidget(hint)

        layout.addWidget(manual_group)

        # ─── Action ───
        self.btn_detect_bands = QPushButton("🔬  Detect Bands")
        self.btn_detect_bands.setObjectName("primaryButton")
        self.btn_detect_bands.setMinimumHeight(36)
        self.btn_detect_bands.clicked.connect(self._detect_bands)
        layout.addWidget(self.btn_detect_bands)
        
        # ─── Lane Profile ───
        self.btn_view_profiles = QPushButton("📈  View Lane Profiles")
        self.btn_view_profiles.setToolTip("Opens a plot showing the lane density, baseline, and peaks to help with manual picking.")
        self.btn_view_profiles.clicked.connect(self._show_lane_profiles)
        layout.addWidget(self.btn_view_profiles)

        # Status label
        self.lbl_band_status = QLabel("")
        self.lbl_band_status.setObjectName("subtitle")
        self.lbl_band_status.setWordWrap(True)
        layout.addWidget(self.lbl_band_status)

        # (band_group was already added above)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    # ── Step 4: Results ──────────────────────────────────────────────

    def _create_step4_results(self) -> QWidget:
        """Create the results page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        results_group = QGroupBox("Normalization")
        results_layout = QVBoxLayout(results_group)

        # Reference lane
        ref_layout = QHBoxLayout()
        ref_layout.addWidget(QLabel("Reference lane:"))
        self.combo_ref_lane = QComboBox()
        self.combo_ref_lane.addItem("None (% of total)")
        self.combo_ref_lane.setToolTip(
            "Select a reference lane for normalization "
            "(e.g., Ponceau S loading control)."
        )
        ref_layout.addWidget(self.combo_ref_lane)
        results_layout.addLayout(ref_layout)

        # Normalize control to 1
        self.chk_normalize_one = QCheckBox("Set control lane to 1.0")
        self.chk_normalize_one.setChecked(True)
        results_layout.addWidget(self.chk_normalize_one)

        # Compute button
        self.btn_compute = QPushButton("📊  Compute Results")
        self.btn_compute.setObjectName("primaryButton")
        self.btn_compute.setMinimumHeight(36)
        self.btn_compute.clicked.connect(self._compute_results)
        results_layout.addWidget(self.btn_compute)

        layout.addWidget(results_group)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    # ── Action Handlers ─────────────────────────────────────────────

    def _open_file(self) -> None:
        """Open a file dialog and load the selected image."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Western Blot Image",
            "",
            "Image Files (*.tif *.tiff *.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if not path:
            return

        try:
            self.analyzer.load_image(path)
            filename = Path(path).name
            self.lbl_filename.setText(f"✅  {filename}")
            self.status_message.emit(f"Loaded: {filename}")

            # Auto-preprocess
            self._preprocess()

        except Exception as e:
            self.lbl_filename.setText(f"❌  Error: {e}")
            self.status_message.emit(f"Error loading file: {e}")
            logger.exception("Error loading image")
            
    def _on_rotation_changed(self, *_args) -> None:
        """Called when rotation is manually adjusted."""
        # Clear manual crop on rotation change to avoid surprising results
        self.analyzer.state.manual_crop_rect = None
        self.btn_manual_crop.setChecked(False)
        self._on_preprocess_changed()
        
    def _on_manual_crop_toggled(self, checked: bool) -> None:
        """Called when manual crop button is toggled."""
        self.crop_mode_toggled.emit(checked)
        if checked:
            self.status_message.emit("Manual Crop: draw a rectangle on the image canvas to crop.")
        else:
            self.status_message.emit("Manual Crop cancelled.")
            
    def on_crop_requested(self, rect) -> None:
        """Received a crop rectangle from the canvas."""
        # QRectF -> tuple[int, int, int, int]
        x = int(round(rect.x()))
        y = int(round(rect.y()))
        w = int(round(rect.width()))
        h = int(round(rect.height()))
        
        self.analyzer.state.manual_crop_rect = (x, y, w, h)
        # Turn off crop mode toggle on UI
        self.btn_manual_crop.setChecked(False) 
        self._preprocess()

    def _on_preprocess_changed(self, *_args) -> None:
        """Called when any preprocessing control is changed.

        Re-runs preprocessing and updates the image canvas in real-time.
        Silently does nothing if no image is loaded yet.
        """
        if self.analyzer.state.original_image is None:
            return
        self._preprocess()

    def _preprocess(self) -> None:
        """Run preprocessing on the loaded image."""
        if self.analyzer.state.original_image is None:
            self.status_message.emit("No image loaded.")
            return

        try:
            invert = "auto" if self.chk_invert.isChecked() else False
            rotation = self.spin_rotation.value()
            auto_crop = self.chk_autocrop.isChecked()
            manual_crop_rect = self.analyzer.state.manual_crop_rect
            contrast = self.spin_contrast.value()

            processed = self.analyzer.preprocess(
                invert_lut=invert,
                rotation_angle=rotation,
                contrast_alpha=contrast,
                manual_crop_rect=manual_crop_rect,
                auto_crop=auto_crop,
            )

            self.image_changed.emit(processed)
            inv_status = " (inverted)" if self.analyzer.state.is_inverted else ""
            rot_status = f", rotated {rotation:.1f}°" if abs(rotation) > 0.01 else ""
            cont_status = f", contrast x{contrast:.1f}" if abs(contrast - 1.0) > 0.01 else ""
            crop_status = ", cropped" if auto_crop else ""
            self.status_message.emit(
                f"Preprocessed{inv_status}{rot_status}{cont_status}{crop_status}"
            )

        except Exception as e:
            self.status_message.emit(f"Preprocessing error: {e}")
            logger.exception("Preprocessing error")

    def _toggle_manual_lanes(self, auto: bool) -> None:
        """Toggle manual lane count input."""
        self.spin_lanes.setEnabled(not auto)

    def _detect_lanes(self) -> None:
        """Run lane detection and populate lane type selectors."""
        try:
            num_lanes = None if self.chk_auto_lanes.isChecked() else self.spin_lanes.value()
            smoothing = self.spin_smoothing.value()

            lanes = self.analyzer.detect_lanes(
                num_lanes=num_lanes,
                smoothing_window=smoothing,
            )

            self.lbl_lane_status.setText(f"✅  Detected {len(lanes)} lanes")
            self.lbl_lane_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.status_message.emit(f"Detected {len(lanes)} lanes")

            # Update reference lane dropdown
            self.combo_ref_lane.clear()
            self.combo_ref_lane.addItem("None (% of total)")
            for i in range(len(lanes)):
                self.combo_ref_lane.addItem(f"Lane {i + 1}")

            # Populate lane type selectors
            self._populate_lane_type_combos(len(lanes))

            self.lanes_detected.emit(lanes)

        except Exception as e:
            self.lbl_lane_status.setText(f"❌  {e}")
            self.lbl_lane_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Lane detection error")

    def _populate_lane_type_combos(self, num_lanes: int) -> None:
        """Create lane type combo boxes for each detected lane.

        Args:
            num_lanes: Number of lanes detected.
        """
        # Clear existing combos
        for combo in self.lane_type_combos:
            combo.setParent(None)
            combo.deleteLater()
        self.lane_type_combos.clear()

        # Remove the "no lanes yet" label
        self.lbl_no_lanes_yet.setVisible(False)

        # Clear any existing widgets from the container layout
        while self.lane_type_container.count():
            item = self.lane_type_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i in range(num_lanes):
            row = QHBoxLayout()
            lbl = QLabel(f"Lane {i + 1}:")
            combo = QComboBox()
            combo.addItems(["Sample", "Ladder", "Exclude"])
            combo.setToolTip(
                "Sample: include in analysis\n"
                "Ladder: molecular weight marker (excluded from density comparison)\n"
                "Exclude: skip entirely"
            )
            self.lane_type_combos.append(combo)

            row.addWidget(lbl)
            row.addWidget(combo)

            container_widget = QWidget()
            container_widget.setLayout(row)
            self.lane_type_container.addWidget(container_widget)

    def _get_lane_types(self) -> dict[int, str]:
        """Get the lane type configuration.

        Returns:
            Dict mapping lane index to type string ("Sample", "Ladder", "Exclude").
        """
        types = {}
        for i, combo in enumerate(self.lane_type_combos):
            types[i] = combo.currentText()
        return types
        
    def _show_lane_profiles(self) -> None:
        """Open the lane profile viewer dialog."""
        if not self.analyzer.state.profiles:
            # Maybe they haven't run Detect Bands yet
            try:
                self._detect_bands()
            except Exception as e:
                self.status_message.emit(f"Could not compute profiles: {e}")
                return
                
        dialog = LaneProfileDialog(self.analyzer.state, self)

        # Wire profile hover/click events so the main window can keep the
        # image canvas in sync with the profile view.
        dialog.profile_hovered.connect(self._on_profile_hovered_from_dialog)
        dialog.profile_clicked.connect(self._on_profile_clicked_from_dialog)
        dialog.profile_range_selected.connect(self._on_profile_range_selected)
        dialog.profile_band_removed.connect(self._on_profile_band_removed)
        dialog.orientation_changed.connect(self._on_orientation_changed)

        dialog.exec()

    def _on_profile_hovered_from_dialog(self, lane_idx: int, y_pos: float) -> None:
        """Relay profile hover events (lane, y-pos) to the main window."""
        self.profile_hovered.emit(lane_idx, y_pos)

    def _on_profile_clicked_from_dialog(self, lane_idx: int, y_pos: float) -> None:
        """Allow manual band creation by clicking on the profile plot.

        The x-axis of the profile is the vertical position within the lane,
        so we can treat y_pos directly as the lane-relative coordinate.
        """
        if lane_idx < 0 or lane_idx >= len(self.analyzer.state.lanes):
            return
        if not self.analyzer.state.profiles:
            return

        rel_y = int(round(float(y_pos)))
        if rel_y < 0:
            return

        try:
            band = self.analyzer.add_manual_band(lane_idx, rel_y)
        except Exception as e:
            self.status_message.emit(f"Error adding manual band from profile: {e}")
            return

        if band is None:
            self.status_message.emit(
                "No clear peak found near click on profile. "
                "Try clicking closer to the band center."
            )
            return

        lane_types = self._get_lane_types()
        sample_bands = [
            b
            for b in self.analyzer.state.bands
            if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
        ]

        self.bands_detected.emit(self.analyzer.state.bands, self.analyzer.state.lanes)
        self.selected_bands_changed.emit(sample_bands)
        if self._current_step == 3:
            self._compute_results()

    def _on_profile_range_selected(self, lane_idx: int, y_start: float, y_end: float) -> None:
        """Handle range selection from the profile dialog."""
        try:
            band = self.analyzer.add_manual_band_range(lane_idx, y_start, y_end)
        except Exception as e:
            self.status_message.emit(f"Error adding band range: {e}")
            return

        if band:
            lane_types = self._get_lane_types()
            sample_bands = [
                b
                for b in self.analyzer.state.bands
                if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
            ]

            self.bands_detected.emit(self.analyzer.state.bands, self.analyzer.state.lanes)
            self.selected_bands_changed.emit(sample_bands)
            if self._current_step == 3:
                self._compute_results()

    def _on_profile_band_removed(self, lane_idx: int, y_pos: float) -> None:
        """Handle band removal from the profile dialog."""
        if self.analyzer.remove_band_at(lane_idx, y_pos):
            self.status_message.emit(f"Removed band in lane {lane_idx + 1}")
            
            lane_types = self._get_lane_types()
            sample_bands = [
                b
                for b in self.analyzer.state.bands
                if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
            ]

            self.bands_detected.emit(self.analyzer.state.bands, self.analyzer.state.lanes)
            self.selected_bands_changed.emit(sample_bands)
            if self._current_step == 3:
                self._compute_results()
            
            # Refresh the dialog plot
            if isinstance(self.sender(), LaneProfileDialog):
                self.sender()._update_plot()
                
    def _on_orientation_changed(self, lane_idx: int, force_valleys: bool) -> None:
        """Handle manual orientation flip for a specific lane."""
        try:
            # Re-run detection for just this lane with the override
            min_snr = self.spin_snr.value()
            min_distance = self.spin_peak_distance.value()
            max_width = self.spin_max_width.value()
            min_width = self.spin_min_width.value()
            edge_margin = self.spin_edge_margin.value()
            baseline_text = self.combo_baseline.currentText()
            baseline_method = "rolling_ball" if "Rolling" in baseline_text else "linear"
            radius = self.spin_radius.value()

            self.analyzer.detect_bands_for_lane(
                lane_idx,
                force_valleys_as_bands=force_valleys,
                min_peak_distance=min_distance,
                min_snr=min_snr,
                max_band_width=max_width,
                min_band_width=min_width,
                edge_margin_percent=edge_margin,
                baseline_method=baseline_method,
                baseline_radius=radius,
            )
            
            self.status_message.emit(f"Flipped orientation for lane {lane_idx + 1}")
            
            lane_types = self._get_lane_types()
            sample_bands = [
                b
                for b in self.analyzer.state.bands
                if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
            ]

            self.bands_detected.emit(self.analyzer.state.bands, self.analyzer.state.lanes)
            self.selected_bands_changed.emit(sample_bands)
            if self._current_step == 3:
                self._compute_results()

            # Refresh the dialog plot
            if isinstance(self.sender(), LaneProfileDialog):
                self.sender()._update_plot()
                
        except Exception as e:
            self.status_message.emit(f"Error flipping orientation: {e}")
            logger.exception("Orientation flip error")

    def _detect_bands(self) -> None:
        """Run band detection with improved parameters."""
        try:
            min_snr = self.spin_snr.value()
            min_distance = self.spin_peak_distance.value()
            max_width = self.spin_max_width.value()
            min_width = self.spin_min_width.value()
            edge_margin = self.spin_edge_margin.value()
            baseline_text = self.combo_baseline.currentText()
            baseline_method = "rolling_ball" if "Rolling" in baseline_text else "linear"
            radius = self.spin_radius.value()

            manual_pick = bool(self.chk_manual_pick.isChecked())
            bands = self.analyzer.detect_bands(
                min_peak_height=0.02,  # Low absolute threshold; SNR does the filtering
                min_peak_distance=min_distance,
                min_snr=min_snr,
                max_band_width=max_width,
                min_band_width=min_width,
                edge_margin_percent=edge_margin,
                baseline_method=baseline_method,
                baseline_radius=radius,
                manual_pick=manual_pick,
                force_valleys_as_bands=None,  # Reset to auto by default
            )

            # Filter bands based on lane types
            lane_types = self._get_lane_types()
            sample_bands = [
                b for b in bands
                if lane_types.get(b.lane_index, "Sample") == "Sample"
            ]

            # Build per-lane summary for status
            lane_band_counts = {}
            for b in bands:
                lane_band_counts.setdefault(b.lane_index, 0)
                lane_band_counts[b.lane_index] += 1

            summary_parts = []
            for lane_idx in sorted(lane_band_counts):
                lane_type = lane_types.get(lane_idx, "Sample")
                count = lane_band_counts[lane_idx]
                type_tag = f" [{lane_type[0]}]" if lane_type != "Sample" else ""
                summary_parts.append(f"L{lane_idx + 1}: {count}{type_tag}")

            summary = " | ".join(summary_parts)

            if manual_pick:
                self.lbl_band_status.setText(
                    "✅  Profiles computed. Click bands in the image to add peaks.\n"
                    f"{summary}"
                )
            else:
                self.lbl_band_status.setText(
                    f"✅  {len(bands)} bands total ({len(sample_bands)} in sample lanes)\n"
                    f"{summary}"
                )
            self.lbl_band_status.setStyleSheet(f"color: {Colors.SUCCESS};")
            self.status_message.emit(
                f"Detected {len(bands)} bands ({len(sample_bands)} sample)"
            )

            self.bands_detected.emit(bands, self.analyzer.state.lanes)
            self.selected_bands_changed.emit(sample_bands)

        except Exception as e:
            self.lbl_band_status.setText(f"❌  {e}")
            self.lbl_band_status.setStyleSheet(f"color: {Colors.ACCENT_DANGER};")
            logger.exception("Band detection error")

    def _on_manual_pick_toggled(self, enabled: bool) -> None:
        self._manual_peak_picking = bool(enabled)
        self.peak_picking_enabled.emit(self._manual_peak_picking)
        if self._manual_peak_picking:
            self.status_message.emit("Manual peak picking enabled: click 'Detect Bands' then click bands to add peaks.")
        else:
            self.status_message.emit("Manual peak picking disabled.")

    def on_peak_pick_requested(self, x: float, y: float) -> None:
        """Handle manual peak picking clicks on the image canvas."""
        if not self._manual_peak_picking:
            return
        if self._current_step < 2:
            return
        if not self.analyzer.state.lanes:
            return

        lane = None
        for ln in self.analyzer.state.lanes:
            if ln.x_start <= x <= ln.x_end and ln.y_start <= y <= ln.y_end:
                lane = ln
                break
        if lane is None:
            return

        if not self.analyzer.state.profiles:
            try:
                self._detect_bands()
            except Exception as e:
                self.status_message.emit(f"Could not compute profiles for manual picking: {e}")
                return

        rel_y = int(round(float(y) - float(lane.y_start)))
        try:
            band = self.analyzer.add_manual_band(lane.index, rel_y)
        except Exception as e:
            self.status_message.emit(f"Error adding manual band: {e}")
            return
            
        if band is None:
            self.status_message.emit("No clear peak found near click. Try clicking closer to the band center.")
            return

        lane_types = self._get_lane_types()
        sample_bands = [
            b
            for b in self.analyzer.state.bands
            if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
        ]

        self.bands_detected.emit(self.analyzer.state.bands, self.analyzer.state.lanes)
        self.selected_bands_changed.emit(sample_bands)
        if self._current_step == 3:
            self._compute_results()

    def _compute_results(self) -> None:
        """Compute and emit densitometry results."""
        try:
            ref_idx = self.combo_ref_lane.currentIndex()
            reference_lane = ref_idx - 1 if ref_idx > 0 else None
            normalize_one = self.chk_normalize_one.isChecked()

            lane_types = self._get_lane_types()

            df = self.analyzer.compute_densitometry(
                reference_lane=reference_lane,
                normalize_control_to_one=normalize_one,
                lane_types=lane_types,
            )

            self.status_message.emit(
                f"Results computed: {len(df)} bands analyzed"
            )
            self.results_ready.emit(df)

        except Exception as e:
            self.status_message.emit(f"Error computing results: {e}")
            logger.exception("Densitometry error")

    # ── Navigation ──────────────────────────────────────────────────

    def _go_next(self) -> None:
        """Navigate to the next wizard step."""
        # Auto-run the current step's action on "Next"
        if self._current_step == 0:
            # If image is loaded, preprocess
            if self.analyzer.state.original_image is not None:
                self._preprocess()
            else:
                self.status_message.emit("Please load an image first.")
                return

        elif self._current_step == 1:
            # Auto-detect lanes if not done
            if not self.analyzer.state.lanes:
                self._detect_lanes()

        elif self._current_step == 2:
            # Auto-detect bands if not done
            if not self.analyzer.state.bands:
                self._detect_bands()

        if self._current_step < 3:
            self._current_step += 1
            self.pages.setCurrentIndex(self._current_step)
            self.step_indicator.set_current_step(self._current_step)
            self._update_nav_buttons()

            # Auto-compute results when reaching step 4
            if self._current_step == 3:
                self._compute_results()

    def _go_back(self) -> None:
        """Navigate to the previous wizard step."""
        if self._current_step > 0:
            self._current_step -= 1
            self.pages.setCurrentIndex(self._current_step)
            self.step_indicator.set_current_step(self._current_step)
            self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        """Update Back/Next button states."""
        self.btn_back.setEnabled(self._current_step > 0)
        if self._current_step == 3:
            self.btn_next.setText("✅ Done")
            self.btn_next.setEnabled(False)
        else:
            self.btn_next.setText("Next →")
            self.btn_next.setEnabled(True)

    def on_band_clicked(self, band) -> None:
        """Handle when a user clicks a band overlay on the image canvas.
        
        Args:
            band: DetectedBand instance that was interacted with.
        """
        if self._current_step >= 2:
            # Re-generate the summary text on step 3 
            lane_types = self._get_lane_types()
            sample_bands = [
                b for b in self.analyzer.state.bands
                if lane_types.get(b.lane_index, "Sample") == "Sample" and b.selected
            ]
            
            # Recalculate results if we are actively viewing the results page
            if self._current_step == 3:
                self._compute_results()
            else:
                self.status_message.emit(
                    f"Selected {len(sample_bands)} active bands"
                )
                
            self.selected_bands_changed.emit(sample_bands)
