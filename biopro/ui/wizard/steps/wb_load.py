"""Western Blot — Step 1: Load & Preprocess.

Handles image loading, LUT inversion, rotation, contrast/brightness,
auto-detect, and both manual and auto crop.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors, Fonts
from biopro.ui.wizard.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


def _smart_contrast(image) -> tuple[float, float]:
    """Compute contrast alpha and brightness beta using percentile stretching.

    Uses the 2nd and 98th percentiles of the image to compute a linear
    stretch that maps the meaningful intensity range to [0, 1].  This is
    more robust than min/max stretching for blot images which often have
    bright dust specks or dark corner artifacts.

    Returns:
        (alpha, beta) such that output = clip(alpha * pixel + beta, 0, 1)
    """
    import numpy as np
    flat = image.ravel()
    p2 = float(np.percentile(flat, 2))
    p98 = float(np.percentile(flat, 98))
    span = p98 - p2
    if span < 1e-6:
        return 1.5, -0.7  # fallback to user-preferred defaults
    alpha = round(1.0 / span, 3)
    beta = round(-p2 / span, 3)
    # Clamp to reasonable ranges
    alpha = float(np.clip(alpha, 0.5, 8.0))
    beta = float(np.clip(beta, -2.0, 2.0))
    return alpha, beta


class WBLoadStep(WizardStep):
    """Load an image and apply preprocessing (inversion, rotation, crop)."""

    label = "Load"

    # ── WizardStep interface ──────────────────────────────────────────

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._canvas = None
        self._pending_crop_rect = None  # (r_min, r_max, c_min, c_max) from auto-crop

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # ── File picker ───────────────────────────────────────────────
        file_group = QGroupBox("Image File")
        file_layout = QVBoxLayout(file_group)
        self.btn_open = QPushButton("📁  Open Image File...")
        self.btn_open.setMinimumHeight(40)
        self.btn_open.clicked.connect(self._open_file)
        file_layout.addWidget(self.btn_open)
        self.lbl_filename = QLabel("No file loaded")
        self.lbl_filename.setObjectName("subtitle")
        self.lbl_filename.setWordWrap(True)
        self.lbl_filename.setMinimumHeight(18)
        file_layout.addWidget(self.lbl_filename)
        layout.addWidget(file_group)

        # ── Live adjustments ──────────────────────────────────────────
        live_group = QGroupBox("Live Adjustments  —  preview updates as you type")
        live_layout = QVBoxLayout(live_group)
        live_layout.setSpacing(8)

        self.chk_invert = QCheckBox("Auto-invert (dark bands on white background)")
        self.chk_invert.setChecked(True)
        self.chk_invert.setToolTip(
            "When checked, the image is automatically inverted if needed so that\n"
            "dark bands on a white background become detectable peaks.\n"
            "Uncheck if your image is already the right way around."
        )
        self.chk_invert.toggled.connect(self._on_preprocess_changed)
        live_layout.addWidget(self.chk_invert)

        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-180, 180)
        self.spin_rotation.setValue(0)
        self.spin_rotation.setSuffix("°")
        self.spin_rotation.setSingleStep(0.5)
        self.spin_rotation.setToolTip("Rotates the image in real-time. Positive = counter-clockwise.")
        self.spin_rotation.valueChanged.connect(self._on_rotation_changed)
        live_layout.addLayout(self._row("Rotation:", self.spin_rotation))

        # Quick rotation buttons
        rot_btn_row = QHBoxLayout()
        rot_btn_row.setSpacing(4)
        for label, delta in [("-90°", -90), ("-45°", -45), ("+45°", 45), ("+90°", 90)]:
            btn = QPushButton(label)
            btn.setMinimumHeight(28)
            btn.setToolTip(f"Add {delta}° to current rotation")
            btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};"
                f" border: 1px solid {Colors.BORDER}; border-radius: 5px;"
                f" padding: 3px 6px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: {Colors.BG_LIGHT}; }}"
            )
            # Capture delta in closure
            btn.clicked.connect(lambda _, d=delta: self._rotate_by(d))
            rot_btn_row.addWidget(btn)
        live_layout.addLayout(rot_btn_row)

        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.1, 5.0)
        self.spin_contrast.setValue(1.5)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setToolTip(
            "Contrast multiplier. output = α × pixel + β\n"
            ">1.0 = more contrast, <1.0 = less."
        )
        self.spin_contrast.valueChanged.connect(self._on_contrast_manually_changed)
        live_layout.addLayout(self._row("Contrast (α):", self.spin_contrast))

        self.spin_brightness = QDoubleSpinBox()
        self.spin_brightness.setRange(-2.0, 2.0)
        self.spin_brightness.setValue(-0.7)
        self.spin_brightness.setSingleStep(0.05)
        self.spin_brightness.setDecimals(3)
        self.spin_brightness.setToolTip(
            "Brightness offset. output = α × pixel + β\n"
            "Negative = shift darker (useful for high-background images)."
        )
        self.spin_brightness.valueChanged.connect(self._on_preprocess_changed)
        live_layout.addLayout(self._row("Brightness (β):", self.spin_brightness))

        self.btn_reset = QPushButton("↩  Reset to Defaults")
        self.btn_reset.setToolTip("Reset rotation, contrast and brightness to defaults.")
        self.btn_reset.clicked.connect(self._on_reset_preprocess)
        live_layout.addWidget(self.btn_reset)
        layout.addWidget(live_group)

        # ── Smart auto-detect ─────────────────────────────────────────
        auto_group = QGroupBox("Smart Auto-detect")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setSpacing(8)

        hint = QLabel(
            "Click the buttons below to automatically compute optimal values. "
            "Results are applied immediately so you can adjust manually if needed."
        )
        hint.setWordWrap(True)
        hint.setObjectName("subtitle")
        hint.setMinimumHeight(32)
        auto_layout.addWidget(hint)

        auto_btn_row = QHBoxLayout()
        auto_btn_row.setSpacing(6)

        self.btn_auto_rotation = QPushButton("🔄  Auto Rotation")
        self.btn_auto_rotation.setMinimumHeight(36)
        self.btn_auto_rotation.setToolTip(
            "Automatically detect and apply the optimal rotation angle."
        )
        self.btn_auto_rotation.clicked.connect(self._on_auto_rotation)
        auto_btn_row.addWidget(self.btn_auto_rotation)

        self.btn_auto_contrast = QPushButton("🎨  Auto Contrast")
        self.btn_auto_contrast.setMinimumHeight(36)
        self.btn_auto_contrast.setToolTip(
            "Automatically compute optimal contrast (α) and brightness (β)\n"
            "using percentile-based stretching for blot images."
        )
        self.btn_auto_contrast.clicked.connect(self._on_auto_contrast)
        auto_btn_row.addWidget(self.btn_auto_contrast)

        auto_layout.addLayout(auto_btn_row)

        self.btn_auto_crop = QPushButton("✂️  Auto-crop to Band Region")
        self.btn_auto_crop.setMinimumHeight(36)
        self.btn_auto_crop.setToolTip(
            "Detects where the bands are and shows a preview outline.\n"
            "Click 'Confirm Crop' to apply, or 'Cancel' to discard."
        )
        self.btn_auto_crop.clicked.connect(self._on_auto_crop_bands)
        auto_layout.addWidget(self.btn_auto_crop)

        confirm_row = QHBoxLayout()
        self.btn_confirm_crop = QPushButton("✅  Confirm Crop")
        self.btn_confirm_crop.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f" border: none; border-radius: 6px; padding: 7px 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
            f"QPushButton:pressed {{ background-color: {Colors.ACCENT_PRIMARY_PRESSED}; }}"
        )
        self.btn_confirm_crop.setMinimumHeight(34)
        self.btn_confirm_crop.setVisible(False)
        self.btn_confirm_crop.clicked.connect(self._on_confirm_crop)
        confirm_row.addWidget(self.btn_confirm_crop)

        self.btn_cancel_crop = QPushButton("✖  Cancel")
        self.btn_cancel_crop.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: 7px 14px; }}"
            f"QPushButton:hover {{ background-color: {Colors.BG_LIGHT}; }}"
        )
        self.btn_cancel_crop.setMinimumHeight(34)
        self.btn_cancel_crop.setVisible(False)
        self.btn_cancel_crop.clicked.connect(self._on_cancel_crop)
        confirm_row.addWidget(self.btn_cancel_crop)
        auto_layout.addLayout(confirm_row)

        self.lbl_auto_result = QLabel("")
        self.lbl_auto_result.setObjectName("subtitle")
        self.lbl_auto_result.setWordWrap(True)
        self.lbl_auto_result.setMinimumHeight(18)
        auto_layout.addWidget(self.lbl_auto_result)
        layout.addWidget(auto_group)

        # ── Manual crop ───────────────────────────────────────────────
        crop_group = QGroupBox("Manual Crop")
        crop_layout = QVBoxLayout(crop_group)
        crop_layout.setSpacing(8)

        crop_hint = QLabel("Draw a rectangle directly on the image to crop it.")
        crop_hint.setWordWrap(True)
        crop_hint.setObjectName("subtitle")
        crop_hint.setMinimumHeight(18)
        crop_layout.addWidget(crop_hint)

        self.btn_manual_crop = QPushButton("✂️  Start Manual Crop")
        self.btn_manual_crop.setCheckable(True)
        self.btn_manual_crop.setMinimumHeight(34)
        self.btn_manual_crop.setToolTip(
            "Click to enter crop mode, then drag on the image to draw a rectangle."
        )
        self.btn_manual_crop.toggled.connect(self._on_manual_crop_toggled)
        crop_layout.addWidget(self.btn_manual_crop)

        self.btn_clear_crop = QPushButton("🗑  Clear Crop")
        self.btn_clear_crop.setMinimumHeight(34)
        self.btn_clear_crop.setToolTip("Remove the current crop and restore the full image.")
        self.btn_clear_crop.clicked.connect(self._on_clear_crop)
        crop_layout.addWidget(self.btn_clear_crop)
        layout.addWidget(crop_group)

        layout.addStretch()
        return self._scroll(page)

    def on_enter(self) -> None:
        pass  # nothing to refresh

    def on_next(self, panel: WizardPanel) -> bool:
        """Preprocess image and auto-detect lanes before leaving this step."""
        analyzer = panel.analyzer
        if analyzer.state.original_image is None:
            panel.status_message.emit("Please load an image first.")
            return False
        self._preprocess()
        # Auto-run lane detection so step 2 is pre-populated
        from biopro.ui.wizard.steps.wb_lanes import WBLanesStep
        for step in panel._steps:
            if isinstance(step, WBLanesStep) and step._auto_lanes_checked():
                step.run_detection(panel)
                break
        return True

    def set_canvas(self, canvas) -> None:
        self._canvas = canvas

    # ── File loading ──────────────────────────────────────────────────

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Open Western Blot Image",
            "",
            "Image Files (*.tif *.tiff *.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if not path:
            return
        try:
            self._panel.analyzer.load_image(path)
            self.lbl_filename.setText(f"✅  {Path(path).name}")
            self._panel.status_message.emit(f"Loaded: {Path(path).name}")
            self._preprocess()
        except Exception as e:
            self.lbl_filename.setText(f"❌  Error: {e}")
            self._panel.status_message.emit(f"Error loading file: {e}")
            logger.exception("Error loading image")

    # ── Preprocessing ─────────────────────────────────────────────────

    def _preprocess(self) -> None:
        analyzer = self._panel.analyzer
        if analyzer.state.original_image is None:
            return
        try:
            processed = analyzer.preprocess(
                invert_lut="auto" if self.chk_invert.isChecked() else False,
                rotation_angle=self.spin_rotation.value(),
                contrast_alpha=self.spin_contrast.value(),
                contrast_beta=self.spin_brightness.value(),
                manual_crop_rect=analyzer.state.manual_crop_rect,
            )
            self._panel.image_changed.emit(processed)

            parts = []
            if analyzer.state.is_inverted:
                parts.append("inverted")
            rot = self.spin_rotation.value()
            if abs(rot) > 0.01:
                parts.append(f"rotated {rot:.1f}°")
            alpha = self.spin_contrast.value()
            beta = self.spin_brightness.value()
            if abs(alpha - 1.0) > 0.01 or abs(beta) > 0.001:
                parts.append(f"contrast ×{alpha:.2f}{beta:+.3f}")
            suffix = f" ({', '.join(parts)})" if parts else ""
            self._panel.status_message.emit(f"Preprocessed{suffix}")
        except Exception as e:
            self._panel.status_message.emit(f"Preprocessing error: {e}")
            logger.exception("Preprocessing error")

    def _on_preprocess_changed(self, *_) -> None:
        if self._panel.analyzer.state.original_image is None:
            return
        self._preprocess()

    def _on_rotation_changed(self, *_) -> None:
        # With the layer model, rotation rebuilds base_image but crop rect
        # stays valid (it's in base_image coords).  No need to clear it.
        self._on_preprocess_changed()

    def _on_contrast_manually_changed(self, *_) -> None:
        self._on_preprocess_changed()

    def _on_reset_preprocess(self) -> None:
        for spin in (self.spin_rotation, self.spin_contrast, self.spin_brightness):
            spin.blockSignals(True)
        self.spin_rotation.setValue(0.0)
        self.spin_contrast.setValue(1.5)
        self.spin_brightness.setValue(-0.7)
        for spin in (self.spin_rotation, self.spin_contrast, self.spin_brightness):
            spin.blockSignals(False)
        self.lbl_auto_result.setText("")
        self._on_preprocess_changed()

    # ── Quick rotation ────────────────────────────────────────────────

    def _rotate_by(self, delta: float) -> None:
        """Add delta degrees to current rotation value."""
        current = self.spin_rotation.value()
        new_val = (current + delta + 180) % 360 - 180  # keep in [-180, 180]
        self.spin_rotation.setValue(round(new_val, 1))
        # _on_rotation_changed fires automatically via valueChanged

    # ── Auto-detect (split into rotation + contrast) ──────────────────

    def _on_auto_rotation(self) -> None:
        """Auto-detect optimal rotation angle only."""
        analyzer = self._panel.analyzer
        if analyzer.state.original_image is None:
            self._panel.status_message.emit("Load an image first.")
            return
        try:
            from biopro.analysis.image_utils import auto_detect_rotation
            self.lbl_auto_result.setText("⏳  Detecting rotation…")
            self.btn_auto_rotation.setEnabled(False)
            self.btn_auto_rotation.repaint()

            image = analyzer.state.original_image
            alpha = self.spin_contrast.value()
            beta = self.spin_brightness.value()
            stretched = np.clip(image * alpha + beta, 0.0, 1.0)
            angle = auto_detect_rotation(stretched)

            self.spin_rotation.blockSignals(True)
            self.spin_rotation.setValue(round(angle, 2))
            self.spin_rotation.blockSignals(False)

            msg = f"✅  Rotation: {angle:+.2f}°"
            self.lbl_auto_result.setText(msg)
            self._panel.status_message.emit(f"Auto-rotation complete — {msg}")
            self._preprocess()
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  Rotation detection failed: {e}")
            self._panel.status_message.emit(f"Auto-rotation error: {e}")
            logger.exception("Auto-rotation error")
        finally:
            self.btn_auto_rotation.setEnabled(True)

    def _on_auto_contrast(self) -> None:
        """Auto-detect optimal contrast and brightness using percentile stretching."""
        analyzer = self._panel.analyzer
        if analyzer.state.original_image is None:
            self._panel.status_message.emit("Load an image first.")
            return
        try:
            self.lbl_auto_result.setText("⏳  Computing contrast…")
            self.btn_auto_contrast.setEnabled(False)
            self.btn_auto_contrast.repaint()

            image = analyzer.state.original_image
            alpha, beta = _smart_contrast(image)

            self.spin_contrast.blockSignals(True)
            self.spin_brightness.blockSignals(True)
            self.spin_contrast.setValue(round(alpha, 2))
            self.spin_brightness.setValue(round(beta, 3))
            self.spin_contrast.blockSignals(False)
            self.spin_brightness.blockSignals(False)

            msg = f"✅  Contrast: ×{alpha:.2f}, β={beta:+.3f}"
            self.lbl_auto_result.setText(msg)
            self._panel.status_message.emit(f"Auto-contrast complete — {msg}")
            self._preprocess()
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  Contrast detection failed: {e}")
            self._panel.status_message.emit(f"Auto-contrast error: {e}")
            logger.exception("Auto-contrast error")
        finally:
            self.btn_auto_contrast.setEnabled(True)

    # ── Auto-crop ─────────────────────────────────────────────────────

    def _on_auto_crop_bands(self) -> None:
        analyzer = self._panel.analyzer
        if analyzer.state.processed_image is None:
            self._panel.status_message.emit("Load and preprocess an image first.")
            return
        try:
            from biopro.analysis.image_utils import calculate_band_crop_region
            self.btn_auto_crop.setEnabled(False)
            self.btn_auto_crop.repaint()

            # Use base_image so the detected region is in base_image coordinates
            image = analyzer.state.base_image
            if image is None:
                image = analyzer.state.processed_image
            region = calculate_band_crop_region(
                image,
                dark_threshold=0.85,
                min_band_width_frac=0.01,
                min_band_height_frac=0.01,
                vertical_padding_frac=0.15,
                horizontal_padding_frac=0.10,
                smoothing_window=9,
            )
            # calculate_band_crop_region may return a numpy bool in some
            # code paths — coerce to Python bool to avoid ambiguity errors.
            if region is None or (hasattr(region, "__len__") and len(region) == 0):
                self.lbl_auto_result.setText("⚠️  No band region detected.")
                self._panel.status_message.emit("Auto-crop failed: no band region found.")
                return

            r_min, r_max, c_min, c_max = (int(v) for v in region)
            if r_min >= r_max or c_min >= c_max:
                self.lbl_auto_result.setText("⚠️  No valid band region found.")
                self._panel.status_message.emit("Auto-crop failed: invalid region.")
                return

            self._pending_crop_rect = (r_min, r_max, c_min, c_max)
            if self._canvas is not None:
                self._canvas.show_crop_preview(
                    QRectF(c_min, r_min, c_max - c_min, r_max - r_min)
                )
            self.btn_confirm_crop.setVisible(True)
            self.btn_cancel_crop.setVisible(True)
            crop_w, crop_h = c_max - c_min, r_max - r_min
            self.lbl_auto_result.setText(f"📐  Preview: {crop_w}×{crop_h} px. Confirm to apply.")
            self._panel.status_message.emit(f"Crop preview — {crop_w}×{crop_h} px. Confirm or cancel.")
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  Error: {e}")
            self._panel.status_message.emit(f"Auto-crop error: {e}")
            logger.exception("Auto-crop error")
        finally:
            self.btn_auto_crop.setEnabled(True)

    def _on_confirm_crop(self) -> None:
        if self._pending_crop_rect is None:
            return
        try:
            bounds = None
            if self._canvas is not None and hasattr(self._canvas, "get_current_crop_preview_bounds"):
                bounds = self._canvas.get_current_crop_preview_bounds()
            r_min, r_max, c_min, c_max = bounds if bounds else self._pending_crop_rect

            # Clamp against base_image dimensions (crop rect is in base coords)
            base = self._panel.analyzer.state.base_image
            image = base if base is not None else self._panel.analyzer.state.processed_image
            h, w = image.shape[:2]
            r_min = max(0, min(r_min, h - 1))
            r_max = max(r_min + 1, min(r_max, h))
            c_min = max(0, min(c_min, w - 1))
            c_max = max(c_min + 1, min(c_max, w))

            self._panel.analyzer.state.manual_crop_rect = (c_min, r_min, c_max - c_min, r_max - r_min)
            self._preprocess()
            self.lbl_auto_result.setText(f"✅  Cropped to {c_max - c_min}×{r_max - r_min} px.")
            self._panel.status_message.emit("Band region crop applied.")
        except Exception as e:
            self._panel.status_message.emit(f"Crop error: {e}")
            logger.exception("Confirm crop error")
        finally:
            self._pending_crop_rect = None
            self.btn_confirm_crop.setVisible(False)
            self.btn_cancel_crop.setVisible(False)
            if self._canvas is not None:
                self._canvas.clear_crop_preview()

    def _on_cancel_crop(self) -> None:
        self._pending_crop_rect = None
        self.btn_confirm_crop.setVisible(False)
        self.btn_cancel_crop.setVisible(False)
        if self._canvas is not None:
            self._canvas.clear_crop_preview()
        self.lbl_auto_result.setText("Crop cancelled.")
        self._panel.status_message.emit("Crop cancelled.")

    # ── Manual crop ───────────────────────────────────────────────────

    def _on_manual_crop_toggled(self, checked: bool) -> None:
        self._panel.crop_mode_toggled.emit(checked)
        if checked:
            # Show base_image so crop rect coords land in base space.
            base = self._panel.analyzer.state.base_image
            if base is not None:
                self._panel.image_changed.emit(base)
            # If a crop is already set, show it as a draggable preview
            # so the user can fine-tune rather than redraw from scratch.
            crop = self._panel.analyzer.state.manual_crop_rect
            if crop is not None and self._canvas is not None:
                from PyQt6.QtCore import QRectF
                x, y, w, h = crop
                self._canvas.show_crop_preview(QRectF(x, y, w, h))
            self._panel.status_message.emit(
                "Crop mode: drag the handles to adjust, or draw a new rectangle. "
                "Click Confirm to apply."
            )
        else:
            # Restore the analysis (cropped) view and clear preview
            if self._canvas is not None:
                self._canvas.clear_crop_preview()
            processed = self._panel.analyzer.state.processed_image
            if processed is not None:
                self._panel.image_changed.emit(processed)
            self._panel.status_message.emit("Manual crop cancelled.")

    def on_crop_requested(self, rect, panel: WizardPanel) -> None:
        # Canvas is showing base_image during crop mode, so rect coords
        # are in base_image coordinates — exactly what manual_crop_rect needs.
        x, y = int(round(rect.x())), int(round(rect.y()))
        w, h = int(round(rect.width())), int(round(rect.height()))
        panel.analyzer.state.manual_crop_rect = (x, y, w, h)
        self.btn_manual_crop.setChecked(False)
        self._preprocess()

    def _on_clear_crop(self) -> None:
        self._panel.analyzer.state.manual_crop_rect = None
        self.btn_manual_crop.setChecked(False)
        self._preprocess()
        self._panel.status_message.emit("Crop cleared — showing full image.")