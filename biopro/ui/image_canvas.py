"""Zoomable, pannable image canvas based on QGraphicsView.

This widget provides a high-quality image viewer with:
    - Mouse wheel zoom (centered on cursor).
    - Middle-click or Ctrl+click pan.
    - Overlay support for drawing lane boundaries and band detections.
    - Fit-to-view on initial load.
    - Crop preview overlay (dashed orange outline).

The canvas is designed to be general-purpose — it can display any
image and accept arbitrary overlay items.

Usage::

    canvas = ImageCanvas()
    canvas.set_image(my_numpy_array)
    canvas.add_lane_overlay(lane_roi)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QPen, QBrush, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
)

from biopro.analysis.peak_analysis import DetectedBand
from biopro.analysis.lane_detection import LaneROI
from biopro.ui.theme import Colors


class BandOverlayItem(QGraphicsRectItem):
    """Interactive rectangle for a detected band on the canvas.
    
    Can be clicked to toggle its 'selected' state, which updates
    its color and the underlying DetectedBand object.
    """
    
    def __init__(self, rect: QRectF, band: DetectedBand, color: QColor, callback) -> None:
        super().__init__(rect)
        self.band = band
        self.base_color = color
        self.callback = callback
        
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._update_style()
        
    def _update_style(self):
        if self.band.selected:
            c = QColor(self.base_color)
            c.setAlpha(180)
            self.setPen(QPen(c, 1))
            bg = QColor(c)
            bg.setAlpha(40)
            self.setBrush(bg)
        else:
            c = QColor(Colors.FG_SECONDARY)
            c.setAlpha(100)
            self.setPen(QPen(c, 1, Qt.PenStyle.DashLine))
            bg = QColor(c)
            bg.setAlpha(0)
            self.setBrush(bg)
            
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.band.selected = not self.band.selected
            self._update_style()
            if self.callback:
                self.callback(self.band)
            event.accept()
        else:
            super().mousePressEvent(event)


class ImageCanvas(QGraphicsView):
    """Zoomable, pannable image viewer with overlay support.

    Displays a single image with support for:
        - Smooth zoom with mouse wheel.
        - Pan by dragging with middle button or Ctrl+left click.
        - Lane boundary overlays with semi-transparent rectangles.
        - Band position overlays.
        - Crop preview overlay: show_crop_preview() / clear_crop_preview()

    Signals:
        image_loaded: Emitted when a new image is set.
        zoom_changed: Emitted when the zoom level changes.
        band_clicked: Emitted when a band overlay is clicked.
        peak_pick_requested: Emitted when the user clicks in peak-pick mode.
        crop_requested: Emitted when the user draws a manual crop rectangle.
    """

    image_loaded = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    band_clicked = pyqtSignal(object)
    peak_pick_requested = pyqtSignal(float, float)
    crop_requested = pyqtSignal(QRectF)

    _MIN_ZOOM = 0.1
    _MAX_ZOOM = 20.0
    _ZOOM_STEP = 1.15

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._zoom_factor = 1.0
        self._lane_overlays: list[QGraphicsRectItem] = []
        self._band_overlays: list[QGraphicsRectItem] = []
        self._hover_overlay: Optional[QGraphicsRectItem] = None
        self._peak_picking_enabled = False

        # Manual crop-draw state
        self._crop_mode = False
        self._crop_start_pos = None
        self._crop_rect_item: Optional[QGraphicsRectItem] = None

        # Auto/band-region crop preview overlay
        self._crop_preview_item: Optional[QGraphicsRectItem] = None

        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setStyleSheet(
            f"QGraphicsView {{ border: 1px solid {Colors.BORDER}; "
            f"background-color: {Colors.BG_DARKEST}; }}"
        )

    # ── Image display ─────────────────────────────────────────────────

    def set_image(self, image: NDArray[np.float64]) -> None:
        """Display a grayscale float64 image."""
        self.clear_overlays()
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
        self._scene.clear()
        self._pixmap_item = None
        # clear_overlays() already nulled _crop_preview_item

        img_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        h, w = img_uint8.shape[:2]

        if img_uint8.ndim == 2:
            qimage = QImage(img_uint8.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
        else:
            qimage = QImage(img_uint8.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect().toRectF()))

        self._zoom_factor = 1.0
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_loaded.emit()

    # ── Crop preview overlay ──────────────────────────────────────────

    def show_crop_preview(self, rect: QRectF) -> None:
        """Draw a dashed orange outline showing the proposed crop region.

        Non-destructive preview — does not modify the image.
        Call clear_crop_preview() to dismiss, or it is cleared automatically
        when set_image() is next called.

        Args:
            rect: Proposed crop rectangle in scene (image pixel) coordinates.
        """
        self.clear_crop_preview()

        pen = QPen(QColor("#FF8C00"), 2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)          # constant screen-space width at any zoom
        fill = QColor("#FF8C00")
        fill.setAlpha(20)              # barely-there tint so the region is obvious

        self._crop_preview_item = self._scene.addRect(rect, pen, QBrush(fill))
        self._crop_preview_item.setZValue(5)   # above image, below lane/band overlays

    def clear_crop_preview(self) -> None:
        """Remove the crop preview outline from the canvas."""
        if self._crop_preview_item is not None:
            try:
                self._scene.removeItem(self._crop_preview_item)
            except RuntimeError:
                pass   # scene may already be cleared
            self._crop_preview_item = None

    # ── Lane / band overlays ──────────────────────────────────────────

    def add_lane_overlays(self, lanes: list[LaneROI]) -> None:
        """Draw semi-transparent lane boundary overlays."""
        self.clear_lane_overlays()

        colors = Colors.CHART_COLORS
        for i, lane in enumerate(lanes):
            color = QColor(colors[i % len(colors)])
            color.setAlpha(40)

            rect = self._scene.addRect(
                lane.x_start, lane.y_start, lane.width, lane.height,
                QPen(QColor(colors[i % len(colors)]), 2),
                QBrush(color),
            )
            self._lane_overlays.append(rect)

            label = self._scene.addText(str(i + 1))
            label.setDefaultTextColor(QColor(colors[i % len(colors)]))
            label.setPos(lane.center_x - 5, lane.y_start + 5)
            label_font = label.font()
            label_font.setPointSize(max(8, min(20, lane.width // 4)))
            label_font.setBold(True)
            label.setFont(label_font)
            self._lane_overlays.append(label)

    def add_band_overlays(self, lanes: list[LaneROI], bands: list) -> None:
        """Draw band position markers on the image."""
        self.clear_band_overlays()

        for band in bands:
            if band.lane_index >= len(lanes):
                continue

            lane = lanes[band.lane_index]
            color = QColor(Colors.ACCENT_WARNING)
            color.setAlpha(180)

            band_height = max(3, int(band.width))
            rect_geom = QRectF(
                lane.x_start + 2,
                band.position - band_height // 2,
                lane.width - 4,
                band_height,
            )
            item = BandOverlayItem(rect_geom, band, color, callback=self._on_band_toggled)
            self._scene.addItem(item)
            self._band_overlays.append(item)

    def _on_band_toggled(self, band: DetectedBand) -> None:
        self.band_clicked.emit(band)

    def clear_lane_overlays(self) -> None:
        for item in self._lane_overlays:
            self._scene.removeItem(item)
        self._lane_overlays.clear()

    def clear_band_overlays(self) -> None:
        for item in self._band_overlays:
            self._scene.removeItem(item)
        self._band_overlays.clear()

    def hide_hover_indicator(self) -> None:
        if self._hover_overlay:
            self._scene.removeItem(self._hover_overlay)
            self._hover_overlay = None

    def show_hover_indicator(self, lane: LaneROI, y_position: float) -> None:
        if y_position < 0:
            self.hide_hover_indicator()
            return

        if self._hover_overlay is None:
            color = QColor(Colors.ACCENT_PRIMARY)
            color.setAlpha(150)
            rect_geom = QRectF(lane.x_start + 2, y_position - 1.5, lane.width - 4, 3)
            self._hover_overlay = self._scene.addRect(
                rect_geom, QPen(Qt.PenStyle.NoPen), QBrush(color)
            )
            self._hover_overlay.setZValue(10)
        else:
            self._hover_overlay.setRect(
                QRectF(lane.x_start + 2, y_position - 1.5, lane.width - 4, 3)
            )

    def clear_overlays(self) -> None:
        """Remove all overlays (lanes, bands, hover indicator, crop preview)."""
        self.clear_lane_overlays()
        self.clear_band_overlays()
        self.hide_hover_indicator()
        self.clear_crop_preview()

    def fit_to_view(self) -> None:
        if self._pixmap_item:
            self._zoom_factor = 1.0
            self.resetTransform()
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # ── Event Handlers ────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            factor = self._ZOOM_STEP
        elif delta < 0:
            factor = 1.0 / self._ZOOM_STEP
        else:
            return

        new_zoom = self._zoom_factor * factor
        if self._MIN_ZOOM <= new_zoom <= self._MAX_ZOOM:
            self._zoom_factor = new_zoom
            self.scale(factor, factor)
            self.zoom_changed.emit(self._zoom_factor)

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled
        if not enabled and self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
            self._crop_start_pos = None

    def mousePressEvent(self, event) -> None:
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton:
            self._crop_start_pos = self.mapToScene(event.position().toPoint())
            if self._crop_rect_item is None:
                color = QColor(Colors.ACCENT_PRIMARY)
                pen = QPen(color, 2, Qt.PenStyle.DashLine)
                brush = QColor(color)
                brush.setAlpha(30)
                self._crop_rect_item = self._scene.addRect(
                    QRectF(self._crop_start_pos, self._crop_start_pos), pen, brush
                )
            else:
                self._crop_rect_item.setRect(QRectF(self._crop_start_pos, self._crop_start_pos))
            event.accept()
            return

        if (
            self._peak_picking_enabled
            and event.button() == Qt.MouseButton.LeftButton
            and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            pos = self.mapToScene(event.position().toPoint())
            self.peak_pick_requested.emit(float(pos.x()), float(pos.y()))
            event.accept()
            return

        if (
            event.button() == Qt.MouseButton.MiddleButton
            or (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._crop_mode and self._crop_start_pos is not None:
            current_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._crop_start_pos, current_pos).normalized()

            if self._pixmap_item:
                img_rect = self._pixmap_item.boundingRect()
                rect = rect.intersected(img_rect)

            if self._crop_rect_item:
                self._crop_rect_item.setRect(rect)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def set_peak_picking_enabled(self, enabled: bool) -> None:
        self._peak_picking_enabled = bool(enabled)

    def mouseReleaseEvent(self, event) -> None:
        if (
            self._crop_mode
            and event.button() == Qt.MouseButton.LeftButton
            and self._crop_start_pos is not None
        ):
            if self._crop_rect_item:
                rect = self._crop_rect_item.rect()
                if rect.width() > 10 and rect.height() > 10:
                    self.crop_requested.emit(rect)
            self._crop_start_pos = None
            event.accept()
            return

        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)