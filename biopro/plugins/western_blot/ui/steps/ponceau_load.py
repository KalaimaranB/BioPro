"""Ponceau Stain — Step 1: Load & Preprocess.

Identical UI to WBLoadStep but with Ponceau-appropriate defaults:
- Higher default contrast (faint pink bands need boosting)
- Hint text explaining this is the Ponceau image, not the WB image
"""

from __future__ import annotations

import logging
from pathlib import Path

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

from biopro.ui.theme import Colors
from biopro.plugins.western_blot.ui.base import WizardPanel, WizardStep

logger = logging.getLogger(__name__)


def _smart_contrast_ponceau(image) -> tuple[float, float]:
    """Percentile-based contrast for Ponceau images.

    Same as _smart_contrast but enforces a minimum alpha of 2.0
    because Ponceau bands are faint and need aggressive stretching.
    """
    import numpy as np
    flat = image.ravel()
    p2 = float(np.percentile(flat, 2))
    p98 = float(np.percentile(flat, 98))
    span = p98 - p2
    if span < 1e-6:
        return 2.5, -0.7
    alpha = round(1.0 / span, 3)
    beta = round(-p2 / span, 3)
    alpha = float(np.clip(max(alpha, 2.0), 0.5, 10.0))  # Ponceau min 2.0
    beta = float(np.clip(beta, -2.0, 2.0))
    return alpha, beta


class PonceauLoadStep(WizardStep):
    """Load and preprocess the Ponceau S stain image."""

    label = "Pon. Load"

    def build_page(self, panel: WizardPanel) -> QWidget:
        self._panel = panel
        self._canvas = None
        self._pending_crop_rect = None

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Context banner
        banner = QLabel(
            "📌  Load the Ponceau S stain image of the same membrane.\n"
            "This is used to measure total protein per lane for loading normalisation.\n"
            "The WB image is loaded in the next stage."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            f"background: {Colors.BG_DARK}; color: {Colors.FG_SECONDARY};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 6px;"
            f" padding: 10px; font-size: 11px;"
        )
        layout.addWidget(banner)

        # File picker
        file_group = QGroupBox("Ponceau S Image")
        file_layout = QVBoxLayout(file_group)
        self.btn_open = QPushButton("📁  Open Ponceau Image File...")
        self.btn_open.setMinimumHeight(40)
        self.btn_open.clicked.connect(self._open_file)
        file_layout.addWidget(self.btn_open)
        self.lbl_filename = QLabel("No file loaded")
        self.lbl_filename.setObjectName("subtitle")
        self.lbl_filename.setWordWrap(True)
        self.lbl_filename.setMinimumHeight(18)
        file_layout.addWidget(self.lbl_filename)
        layout.addWidget(file_group)

        # Live adjustments — higher contrast defaults for faint pink bands
        live_group = QGroupBox("Live Adjustments  —  preview updates as you type")
        live_layout = QVBoxLayout(live_group)
        live_layout.setSpacing(8)

        self.chk_invert = QCheckBox("Auto-invert (pink bands on white background)")
        self.chk_invert.setChecked(True)
        self.chk_invert.setToolTip(
            "Ponceau S bands are pink on white — after grayscale conversion\n"
            "they appear as dark bands on a light background.\n"
            "Auto-invert detects this and flips appropriately."
        )
        self.chk_invert.toggled.connect(self._on_preprocess_changed)
        live_layout.addWidget(self.chk_invert)

        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-180, 180)
        self.spin_rotation.setValue(0)
        self.spin_rotation.setSuffix("°")
        self.spin_rotation.setSingleStep(0.5)
        self.spin_rotation.setToolTip("Rotate image. Positive = counter-clockwise.")
        self.spin_rotation.valueChanged.connect(self._on_rotation_changed)
        live_layout.addLayout(self._row("Rotation:", self.spin_rotation))

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
            btn.clicked.connect(lambda _, d=delta: self._rotate_by(d))
            rot_btn_row.addWidget(btn)
        live_layout.addLayout(rot_btn_row)

        # Higher default contrast — Ponceau bands are faint
        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.1, 10.0)
        self.spin_contrast.setValue(2.5)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setToolTip(
            "Contrast multiplier. Ponceau bands are faint — start high (2–4×).\n"
            "output = α × pixel + β"
        )
        self.spin_contrast.valueChanged.connect(self._on_preprocess_changed)
        live_layout.addLayout(self._row("Contrast (α):", self.spin_contrast))

        self.spin_brightness = QDoubleSpinBox()
        self.spin_brightness.setRange(-2.0, 2.0)
        self.spin_brightness.setValue(-0.5)
        self.spin_brightness.setSingleStep(0.05)
        self.spin_brightness.setDecimals(3)
        self.spin_brightness.setToolTip(
            "Brightness offset. Negative darkens background — helps separate\n"
            "faint Ponceau bands from the white membrane background."
        )
        self.spin_brightness.valueChanged.connect(self._on_preprocess_changed)
        live_layout.addLayout(self._row("Brightness (β):", self.spin_brightness))

        self.btn_reset = QPushButton("↩  Reset to Defaults")
        self.btn_reset.clicked.connect(self._on_reset_preprocess)
        live_layout.addWidget(self.btn_reset)
        layout.addWidget(live_group)

        # Auto-detect
        auto_group = QGroupBox("Smart Auto-detect")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setSpacing(8)

        hint = QLabel(
            "Auto-detect sets rotation and contrast for this image. "
            "Because Ponceau bands are faint, you may want to increase "
            "contrast further manually after auto-detect."
        )
        hint.setWordWrap(True)
        hint.setObjectName("subtitle")
        auto_layout.addWidget(hint)

        auto_btn_row = QHBoxLayout()
        auto_btn_row.setSpacing(6)

        self.btn_auto_rotation = QPushButton("🔄  Auto Rotation")
        self.btn_auto_rotation.setMinimumHeight(36)
        self.btn_auto_rotation.setToolTip("Auto-detect optimal rotation angle.")
        self.btn_auto_rotation.clicked.connect(self._on_auto_rotation)
        auto_btn_row.addWidget(self.btn_auto_rotation)

        self.btn_auto_contrast = QPushButton("🎨  Auto Contrast")
        self.btn_auto_contrast.setMinimumHeight(36)
        self.btn_auto_contrast.setToolTip(
            "Auto-compute contrast/brightness for Ponceau (faint pink bands)."
        )
        self.btn_auto_contrast.clicked.connect(self._on_auto_contrast)
        auto_btn_row.addWidget(self.btn_auto_contrast)

        auto_layout.addLayout(auto_btn_row)

        self.btn_auto_crop = QPushButton("✂️  Auto-crop to Band Region")
        self.btn_auto_crop.setMinimumHeight(36)
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

        # Manual crop
        crop_group = QGroupBox("Manual Crop")
        crop_layout = QVBoxLayout(crop_group)
        crop_layout.setSpacing(8)

        crop_hint = QLabel("Draw a rectangle on the image to crop it.")
        crop_hint.setWordWrap(True)
        crop_hint.setObjectName("subtitle")
        crop_layout.addWidget(crop_hint)

        self.btn_manual_crop = QPushButton("✂️  Start Manual Crop")
        self.btn_manual_crop.setCheckable(True)
        self.btn_manual_crop.setMinimumHeight(34)
        self.btn_manual_crop.toggled.connect(self._on_manual_crop_toggled)
        crop_layout.addWidget(self.btn_manual_crop)

        self.btn_clear_crop = QPushButton("🗑  Clear Crop")
        self.btn_clear_crop.setMinimumHeight(34)
        self.btn_clear_crop.clicked.connect(self._on_clear_crop)
        crop_layout.addWidget(self.btn_clear_crop)
        layout.addWidget(crop_group)

        layout.addStretch()
        return self._scroll(page)

    def on_enter(self) -> None:
        pass

    def on_next(self, panel: WizardPanel) -> bool:
        if panel.ponceau_analyzer.state.original_image is None:
            panel.status_message.emit("Please load a Ponceau image first.")
            return False
        self._preprocess()
        return True

    def set_canvas(self, canvas) -> None:
        self._canvas = canvas

    # ── File loading ──────────────────────────────────────────────────

    def _open_file(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        import logging
        
        logger = logging.getLogger(__name__)

        main_win = self._panel.window()
        pm = getattr(main_win, "project_manager", None)
        default_dir = str(pm.project_dir) if pm else ""

        path, _ = QFileDialog.getOpenFileName(
            self._panel,
            "Open Ponceau S Image",
            default_dir,
            "Image Files (*.tif *.tiff *.png *.jpg *.jpeg *.bmp);;All Files (*)",
        )
        if not path:
            return
            
        final_path = Path(path)
        
        if pm:
            try:
                is_in_workspace = pm.assets_dir.resolve() in final_path.resolve().parents
                
                if not is_in_workspace:
                    reply = QMessageBox.question(
                        self._panel,
                        "Copy to Workspace?",
                        f"The image '{final_path.name}' is outside the project folder.\n\n"
                        "Would you like to copy it into the project's 'assets' folder for safe keeping and portability?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    copy_to_workspace = (reply == QMessageBox.StandardButton.Yes)
                else:
                    copy_to_workspace = False
                    
                file_hash = pm.add_image(final_path, copy_to_workspace)
                resolved_path = pm.get_asset_path(file_hash)
                if resolved_path:
                    final_path = resolved_path
                    
            except Exception as e:
                QMessageBox.warning(self._panel, "Asset Error", f"Failed to add asset to project:\n{e}")
                logger.exception("Asset Management Error")

        try:
            self._panel.ponceau_analyzer.load_image(str(final_path))
            self.lbl_filename.setText(f"✅  {final_path.name}")
            self._panel.status_message.emit(f"Ponceau: Loaded {final_path.name}")
            
            self._on_auto_contrast() 
            
        except Exception as e:
            self.lbl_filename.setText(f"❌  Error: {e}")
            self._panel.status_message.emit(f"Error loading Ponceau image: {e}")
            logger.exception("Error loading Ponceau image")

    # ── Preprocessing ─────────────────────────────────────────────────

    def _preprocess(self) -> None:
        analyzer = self._panel.ponceau_analyzer
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
            self._panel.status_message.emit("Ponceau: Preprocessed")
        except Exception as e:
            self._panel.status_message.emit(f"Ponceau preprocessing error: {e}")
            logger.exception("Ponceau preprocessing error")

    def _on_preprocess_changed(self, *_) -> None:
        if self._panel.ponceau_analyzer.state.original_image is None:
            return
        self._preprocess()

    def _on_rotation_changed(self, *_) -> None:
        # Rotation rebuilds base_image; crop rect stays valid (base coords).
        self._on_preprocess_changed()

    def _on_reset_preprocess(self) -> None:
        for spin in (self.spin_rotation, self.spin_contrast, self.spin_brightness):
            spin.blockSignals(True)
        self.spin_rotation.setValue(0.0)
        self.spin_contrast.setValue(2.5)   # Ponceau default — higher than WB
        self.spin_brightness.setValue(-0.7)
        for spin in (self.spin_rotation, self.spin_contrast, self.spin_brightness):
            spin.blockSignals(False)
        self.lbl_auto_result.setText("")
        self._on_preprocess_changed()

    # ── Auto-detect ───────────────────────────────────────────────────

    def _rotate_by(self, delta: float) -> None:
        current = self.spin_rotation.value()
        new_val = (current + delta + 180) % 360 - 180
        self.spin_rotation.setValue(round(new_val, 1))

    def _on_auto_rotation(self) -> None:
        analyzer = self._panel.ponceau_analyzer
        if analyzer.state.original_image is None:
            self._panel.status_message.emit("Load a Ponceau image first.")
            return
        try:
            import numpy as np
            from biopro.shared.analysis.image_utils import auto_detect_rotation
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
            self._panel.status_message.emit(f"Ponceau auto-rotation: {msg}")
            self._preprocess()
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  {e}")
            logger.exception("Ponceau auto-rotation error")
        finally:
            self.btn_auto_rotation.setEnabled(True)

    def _on_auto_contrast(self) -> None:
        analyzer = self._panel.ponceau_analyzer
        if analyzer.state.original_image is None:
            self._panel.status_message.emit("Load a Ponceau image first.")
            return
        try:
            import numpy as np
            self.lbl_auto_result.setText("⏳  Computing contrast…")
            self.btn_auto_contrast.setEnabled(False)
            self.btn_auto_contrast.repaint()

            image = analyzer.state.original_image
            alpha, beta = _smart_contrast_ponceau(image)

            self.spin_contrast.blockSignals(True)
            self.spin_brightness.blockSignals(True)
            self.spin_contrast.setValue(round(alpha, 2))
            self.spin_brightness.setValue(round(beta, 3))
            self.spin_contrast.blockSignals(False)
            self.spin_brightness.blockSignals(False)

            msg = f"✅  Contrast: ×{alpha:.2f}, β={beta:+.3f}"
            self.lbl_auto_result.setText(msg)
            self._panel.status_message.emit(f"Ponceau auto-contrast: {msg}")
            self._preprocess()
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  {e}")
            logger.exception("Ponceau auto-contrast error")
        finally:
            self.btn_auto_contrast.setEnabled(True)

    # ── Auto-crop ─────────────────────────────────────────────────────

    def _on_auto_crop_bands(self) -> None:
        analyzer = self._panel.ponceau_analyzer
        if analyzer.state.processed_image is None:
            self._panel.status_message.emit("Load and preprocess first.")
            return
        try:
            from biopro.shared.analysis.image_utils import calculate_band_crop_region
            self.btn_auto_crop.setEnabled(False)
            self.btn_auto_crop.repaint()

            region = calculate_band_crop_region(
                analyzer.state.base_image or analyzer.state.processed_image,
                dark_threshold=0.85, min_band_width_frac=0.01,
                min_band_height_frac=0.01, vertical_padding_frac=0.15,
                horizontal_padding_frac=0.10, smoothing_window=9,
            )
            if region is None:
                self.lbl_auto_result.setText("⚠️  No band region detected.")
                return
            # Cast to Python ints — region may be numpy array causing
            # "truth value ambiguous" error with boolean comparisons
            r_min, r_max, c_min, c_max = (int(v) for v in region)
            if r_min >= r_max or c_min >= c_max:
                self.lbl_auto_result.setText("⚠️  No band region detected.")
                return
            self._pending_crop_rect = (r_min, r_max, c_min, c_max)
            if self._canvas is not None:
                self._canvas.show_crop_preview(
                    QRectF(c_min, r_min, c_max - c_min, r_max - r_min)
                )
            self.btn_confirm_crop.setVisible(True)
            self.btn_cancel_crop.setVisible(True)
            self.lbl_auto_result.setText(
                f"📐  Preview: {c_max - c_min}×{r_max - r_min} px. Confirm to apply."
            )
        except Exception as e:
            self.lbl_auto_result.setText(f"❌  {e}")
            logger.exception("Ponceau auto-crop error")
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
            base = self._panel.ponceau_analyzer.state.base_image
            image = base if base is not None else self._panel.ponceau_analyzer.state.processed_image
            h, w = image.shape[:2]
            r_min, r_max = max(0, r_min), max(r_min + 1, min(r_max, h))
            c_min, c_max = max(0, c_min), max(c_min + 1, min(c_max, w))
            self._panel.ponceau_analyzer.state.manual_crop_rect = (
                c_min, r_min, c_max - c_min, r_max - r_min
            )
            self._preprocess()
            self.lbl_auto_result.setText(f"✅  Cropped to {c_max - c_min}×{r_max - r_min} px.")
        except Exception as e:
            self._panel.status_message.emit(f"Crop error: {e}")
            logger.exception("Ponceau confirm crop error")
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

    def _on_manual_crop_toggled(self, checked: bool) -> None:
        self._panel.crop_mode_toggled.emit(checked)
        if checked:
            base = self._panel.ponceau_analyzer.state.base_image
            if base is not None:
                self._panel.image_changed.emit(base)
            self._panel.status_message.emit("Crop mode: draw a rectangle on the full Ponceau image.")
        else:
            processed = self._panel.ponceau_analyzer.state.processed_image
            if processed is not None:
                self._panel.image_changed.emit(processed)
            self._panel.status_message.emit("Manual crop cancelled.")

    def on_crop_requested(self, rect, panel: WizardPanel) -> None:
        # Canvas shows base_image in crop mode — coords are in base space.
        x, y = int(round(rect.x())), int(round(rect.y()))
        w, h = int(round(rect.width())), int(round(rect.height()))
        panel.ponceau_analyzer.state.manual_crop_rect = (x, y, w, h)
        self.btn_manual_crop.setChecked(False)
        self._preprocess()

    def _on_clear_crop(self) -> None:
        self._panel.ponceau_analyzer.state.manual_crop_rect = None
        self.btn_manual_crop.setChecked(False)
        self._preprocess()