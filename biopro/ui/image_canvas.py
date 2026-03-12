"""Zoomable, pannable image canvas based on QGraphicsView.

This widget provides a high-quality image viewer with:
    - Mouse wheel zoom (centered on cursor).
    - Middle-click or Ctrl+click pan.
    - Overlay support for drawing lane boundaries and band detections.
    - Fit-to-view on initial load.

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
        """Initialize band overlay.
        
        Args:
            rect: The bounding rectangle geometry.
            band: The backend DetectedBand data class.
            color: Base color for the active state.
            callback: Function to call when clicked/toggled.
        """
        super().__init__(rect)
        self.band = band
        self.base_color = color
        self.callback = callback
        
        self.setAcceptHoverEvents(True)
        # Allows it to receive mouse clicks
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        
        self._update_style()
        
    def _update_style(self):
        """Update brush and pen based on selected state."""
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
        """Toggle the band's selected state when clicked."""
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

    Signals:
        image_loaded: Emitted when a new image is set.
        zoom_changed: Emitted when the zoom level changes, with the
            new scale factor as argument.

    Attributes:
        _scene: The QGraphicsScene holding all items.
        _pixmap_item: The image pixmap item.
        _zoom_factor: Current cumulative zoom level.
        _lane_overlays: List of overlay items for lane boundaries.
    """

    image_loaded = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    band_clicked = pyqtSignal(object)
    peak_pick_requested = pyqtSignal(float, float)
    crop_requested = pyqtSignal(QRectF)

    # Zoom limits
    _MIN_ZOOM = 0.1
    _MAX_ZOOM = 20.0
    _ZOOM_STEP = 1.15  # 15% per scroll step

    def __init__(self, parent=None) -> None:
        """Initialize the canvas.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._zoom_factor = 1.0
        self._lane_overlays: list[QGraphicsRectItem] = []
        self._band_overlays: list[QGraphicsRectItem] = []
        self._hover_overlay: Optional[QGraphicsRectItem] = None
        self._peak_picking_enabled = False
        
        # Crop mode state
        self._crop_mode = False
        self._crop_start_pos = None
        self._crop_rect_item: Optional[QGraphicsRectItem] = None

        # Configure view
        self.setRenderHints(
            self.renderHints()  # keep existing hints
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Style
        self.setStyleSheet(
            f"QGraphicsView {{ border: 1px solid {Colors.BORDER}; "
            f"background-color: {Colors.BG_DARKEST}; }}"
        )

    def set_image(self, image: NDArray[np.float64]) -> None:
        """Display a grayscale float64 image.

        Converts the NumPy array to a QPixmap and displays it,
        fitting the view to the image.

        Args:
            image: Grayscale float64 array in [0.0, 1.0].
        """
        # Clear existing
        self.clear_overlays()
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
        self._scene.clear()
        self._pixmap_item = None

        # Convert float64 [0, 1] → uint8 [0, 255]
        img_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)

        h, w = img_uint8.shape[:2]

        if img_uint8.ndim == 2:
            # Grayscale → create QImage
            qimage = QImage(
                img_uint8.tobytes(),
                w, h,
                w,  # bytes per line
                QImage.Format.Format_Grayscale8,
            )
        else:
            # RGB
            bytes_per_line = 3 * w
            qimage = QImage(
                img_uint8.tobytes(),
                w, h,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )

        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect().toRectF()))

        # Fit to view
        self._zoom_factor = 1.0
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.image_loaded.emit()

    def add_lane_overlays(self, lanes: list[LaneROI]) -> None:
        """Draw semi-transparent lane boundary overlays.

        Each lane is shown as a colored rectangle with its index label.

        Args:
            lanes: List of LaneROI objects to display.
        """
        self.clear_lane_overlays()

        colors = Colors.CHART_COLORS
        for i, lane in enumerate(lanes):
            color = QColor(colors[i % len(colors)])
            color.setAlpha(40)  # Semi-transparent fill

            rect = self._scene.addRect(
                lane.x_start,
                lane.y_start,
                lane.width,
                lane.height,
                QPen(QColor(colors[i % len(colors)]), 2),
                QBrush(color),
            )
            self._lane_overlays.append(rect)

            # Lane number label
            label = self._scene.addText(str(i + 1))
            label.setDefaultTextColor(QColor(colors[i % len(colors)]))
            label.setPos(
                lane.center_x - 5,
                lane.y_start + 5,
            )
            # Scale label based on image size
            label_font = label.font()
            label_font.setPointSize(max(8, min(20, lane.width // 4)))
            label_font.setBold(True)
            label.setFont(label_font)
            
            # Store label so it gets cleared too
            self._lane_overlays.append(label)

    def add_band_overlays(
        self,
        lanes: list[LaneROI],
        bands: list,
    ) -> None:
        """Draw band position markers on the image.

        Each band is shown as a horizontal line across its lane at
        the detected position.

        Args:
            lanes: Lane ROIs (for x-coordinates).
            bands: List of DetectedBand objects.
        """
        self.clear_band_overlays()

        for band in bands:
            if band.lane_index >= len(lanes):
                continue

            lane = lanes[band.lane_index]
            color = QColor(Colors.ACCENT_WARNING)
            color.setAlpha(180)

            # Draw an interactive rectangle at the band position
            band_height = max(3, int(band.width))
            
            rect_geom = QRectF(
                lane.x_start + 2,
                band.position - band_height // 2,
                lane.width - 4,
                band_height
            )
            
            # Use our custom interactive graphic item
            item = BandOverlayItem(
                rect_geom,
                band,
                color,
                callback=self._on_band_toggled
            )
            
            self._scene.addItem(item)
            self._band_overlays.append(item)
            
    def _on_band_toggled(self, band: DetectedBand) -> None:
        """Propagate band click events to the parent logic."""
        self.band_clicked.emit(band)

    def clear_lane_overlays(self) -> None:
        """Remove all lane boundary overlays."""
        for item in self._lane_overlays:
            self._scene.removeItem(item)
        self._lane_overlays.clear()

    def clear_band_overlays(self) -> None:
        """Remove all band position overlays."""
        for item in self._band_overlays:
            self._scene.removeItem(item)
        self._band_overlays.clear()

    def hide_hover_indicator(self) -> None:
        """Remove the hover indicator if it exists."""
        if self._hover_overlay:
            self._scene.removeItem(self._hover_overlay)
            self._hover_overlay = None

    def show_hover_indicator(self, lane: LaneROI, y_position: float) -> None:
        """Draw a temporary hover indicator across the lane at the given y position."""
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
            self._hover_overlay.setZValue(10)  # Always draw on top
        else:
            self._hover_overlay.setRect(
                QRectF(lane.x_start + 2, y_position - 1.5, lane.width - 4, 3)
            )

    def clear_overlays(self) -> None:
        """Remove all overlays (lanes and bands)."""
        self.clear_lane_overlays()
        self.clear_band_overlays()
        self.hide_hover_indicator()

    def fit_to_view(self) -> None:
        """Reset zoom to fit the entire image in the viewport."""
        if self._pixmap_item:
            self._zoom_factor = 1.0
            self.resetTransform()
            self.fitInView(
                self._scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    # ── Event Handlers ──────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming.

        Zoom in/out centered on the cursor position.
        """
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
        """Enable/disable manual crop mode."""
        self._crop_mode = enabled
        if not enabled and self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
            self._crop_start_pos = None

    def mousePressEvent(self, event) -> None:
        """Handle mouse press for panning or cropping."""
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
            # Simulate a left-button press for the drag handler
            fake_event = event
            super().mousePressEvent(fake_event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for cropping."""
        if self._crop_mode and self._crop_start_pos is not None:
            current_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._crop_start_pos, current_pos).normalized()
            
            # Constrain to image bounds
            if self._pixmap_item:
                img_rect = self._pixmap_item.boundingRect()
                rect = rect.intersected(img_rect)
                
            if self._crop_rect_item:
                self._crop_rect_item.setRect(rect)
            event.accept()
            return
            
        super().mouseMoveEvent(event)

    def set_peak_picking_enabled(self, enabled: bool) -> None:
        """Enable/disable ImageJ-style manual peak picking clicks."""
        self._peak_picking_enabled = bool(enabled)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to stop panning or cropping."""
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton and self._crop_start_pos is not None:
            if self._crop_rect_item:
                rect = self._crop_rect_item.rect()
                if rect.width() > 10 and rect.height() > 10:
                    self.crop_requested.emit(rect)
            self._crop_start_pos = None
            event.accept()
            return
            
        super().mouseReleaseEvent(event)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
