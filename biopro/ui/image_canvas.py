"""Zoomable, pannable image canvas based on QGraphicsView.

This widget provides a high-quality image viewer with:
    - Mouse wheel zoom (centered on cursor).
    - Middle-click or Ctrl+click pan.
    - Overlay support for drawing lane boundaries and band detections.
    - Draggable lane border lines (enabled only on the lanes step).
    - Fit-to-view on initial load.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QPen, QBrush, QCursor, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsLineItem,
    QGraphicsTextItem,
)

from biopro.analysis.peak_analysis import DetectedBand
from biopro.analysis.lane_detection import LaneROI
from biopro.ui.theme import Colors


# ── Band overlay ──────────────────────────────────────────────────────────────

class BandOverlayItem(QGraphicsRectItem):
    """Interactive rectangle for a detected band on the canvas."""

    def __init__(
        self,
        rect: QRectF,
        band: DetectedBand,
        color: QColor,
        callback,
    ) -> None:
        super().__init__(rect)
        self.band = band
        self.base_color = color
        self.callback = callback
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._update_style()

    def set_comparison_slot(self, slot: str | None) -> None:
        """Mark this band as a comparison slot.

        slot can be:
          - None       : no comparison marker
          - 'A' / 'B' : legacy two-slot labels (red / blue)
          - '#rrggbb'  : arbitrary hex color for multi-slot support
        """
        self._comparison_slot = slot
        self._update_style()

    def _update_style(self) -> None:
        slot = getattr(self, "_comparison_slot", None)
        if slot is not None and slot != "":
            # Resolve color: named slots or hex
            if slot == "A":
                hex_color = "#f85149"
            elif slot == "B":
                hex_color = "#58a6ff"
            elif slot.startswith("#"):
                hex_color = slot
            else:
                hex_color = "#2dccb8"  # fallback teal
            c = QColor(hex_color)
            self.setPen(QPen(c, 3))
            bg = QColor(c); bg.setAlpha(70)
            self.setBrush(bg)
            return
        if self.band.selected:
            c = QColor(self.base_color)
            c.setAlpha(180)
            self.setPen(QPen(c, 1))
            bg = QColor(c); bg.setAlpha(40)
            self.setBrush(bg)
        else:
            c = QColor(Colors.FG_SECONDARY)
            c.setAlpha(100)
            self.setPen(QPen(c, 1, Qt.PenStyle.DashLine))
            self.setBrush(QBrush())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Clicking a band sets it for A/B comparison — does NOT toggle
            # analysis inclusion. The callback handles slot assignment.
            if self.callback:
                self.callback(self.band)
            event.accept()
        else:
            super().mousePressEvent(event)


# ── Lane border item ──────────────────────────────────────────────────────────

class LaneBorderItem(QGraphicsLineItem):
    """Draggable vertical line representing a lane boundary.

    The border sits between two adjacent lanes.  When the user drags it
    left or right the canvas emits ``ImageCanvas.lane_border_changed``
    with (border_index, new_x) so the lanes step can rebuild the ROIs.

    ``border_index`` is the index into the boundary list — boundary 0 is
    the left edge of lane 0 (not draggable), boundary 1 is the split
    between lane 0 and lane 1, etc.
    """

    # How many pixels either side of the line counts as "close enough to grab"
    GRAB_TOLERANCE = 8

    def __init__(
        self,
        border_index: int,
        x: float,
        y_top: float,
        y_bottom: float,
        canvas: "ImageCanvas",
    ) -> None:
        super().__init__(x, y_top, x, y_bottom)
        self.border_index = border_index
        self._canvas = canvas
        self._dragging = False
        self._img_width = 0.0

        self._apply_normal_style()
        self.setAcceptHoverEvents(True)
        self.setZValue(20)  # Always on top of lane rects

    def _apply_normal_style(self) -> None:
        pen = QPen(QColor(Colors.ACCENT_PRIMARY), 2, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)  # Constant screen width regardless of zoom
        self.setPen(pen)

    def _apply_hover_style(self) -> None:
        pen = QPen(QColor(Colors.ACCENT_PRIMARY_HOVER), 3, Qt.PenStyle.SolidLine)
        pen.setCosmetic(True)
        self.setPen(pen)

    def hoverEnterEvent(self, event) -> None:
        self._apply_hover_style()
        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        if not self._dragging:
            self._apply_normal_style()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._apply_hover_style()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            new_x = event.scenePos().x()
            # Clamp to image bounds with a small margin
            margin = 4.0
            new_x = max(margin, min(self._img_width - margin, new_x))
            # Move the line
            line = self.line()
            self.setLine(new_x, line.y1(), new_x, line.y2())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._apply_hover_style()  # Keep highlighted until hover leave
            final_x = self.line().x1()
            self._canvas.lane_border_changed.emit(self.border_index, float(final_x))
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ── Resizable crop rect ───────────────────────────────────────────────────────

class ResizableCropItem(QGraphicsRectItem):
    """A crop rectangle with 8 draggable handles for resizing.

    The user can:
    - Drag the interior to move the whole rect.
    - Drag any of the 8 handle dots to resize from that edge/corner.
    The item clamps itself to the image bounds stored in ``_img_rect``.
    """

    HANDLE_SIZE = 10  # diameter of each handle dot
    # Handle indices: 0=TL 1=TC 2=TR 3=ML 4=MR 5=BL 6=BC 7=BR
    _TOP    = {0, 1, 2}
    _BOTTOM = {5, 6, 7}
    _LEFT   = {0, 3, 5}
    _RIGHT  = {2, 4, 7}

    _CURSORS = [
        Qt.CursorShape.SizeFDiagCursor,   # 0 TL
        Qt.CursorShape.SizeVerCursor,      # 1 TC
        Qt.CursorShape.SizeBDiagCursor,    # 2 TR
        Qt.CursorShape.SizeHorCursor,      # 3 ML
        Qt.CursorShape.SizeHorCursor,      # 4 MR
        Qt.CursorShape.SizeBDiagCursor,    # 5 BL
        Qt.CursorShape.SizeVerCursor,      # 6 BC
        Qt.CursorShape.SizeFDiagCursor,    # 7 BR
    ]

    def __init__(self, rect: QRectF, img_rect: QRectF) -> None:
        super().__init__(rect)
        self._img_rect = img_rect
        self._drag_handle: int | None = None   # which handle is being dragged
        self._drag_start: QPointF | None = None
        self._rect_at_drag: QRectF | None = None
        self._moving = False                   # True when dragging the body

        color = QColor(Colors.ACCENT_PRIMARY)
        pen = QPen(color, 2, Qt.PenStyle.DashLine)
        fill = QColor(color)
        fill.setAlpha(25)
        self.setPen(pen)
        self.setBrush(fill)
        self.setZValue(15)
        self.setAcceptHoverEvents(True)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

    # ── Handle geometry ───────────────────────────────────────────────

    def _handle_rects(self) -> list[QRectF]:
        """Return 8 QRectF objects for the handle hit areas."""
        r = self.rect()
        s = self.HANDLE_SIZE
        cx, cy = r.center().x(), r.center().y()
        return [
            QRectF(r.left()  - s/2, r.top()    - s/2, s, s),  # 0 TL
            QRectF(cx        - s/2, r.top()    - s/2, s, s),  # 1 TC
            QRectF(r.right() - s/2, r.top()    - s/2, s, s),  # 2 TR
            QRectF(r.left()  - s/2, cy         - s/2, s, s),  # 3 ML
            QRectF(r.right() - s/2, cy         - s/2, s, s),  # 4 MR
            QRectF(r.left()  - s/2, r.bottom() - s/2, s, s),  # 5 BL
            QRectF(cx        - s/2, r.bottom() - s/2, s, s),  # 6 BC
            QRectF(r.right() - s/2, r.bottom() - s/2, s, s),  # 7 BR
        ]

    def _hit_handle(self, pos: QPointF) -> int | None:
        for i, hr in enumerate(self._handle_rects()):
            if hr.contains(pos):
                return i
        return None

    # ── Drawing ───────────────────────────────────────────────────────

    def paint(self, painter, option, widget=None) -> None:
        # Draw the rect itself
        super().paint(painter, option, widget)
        # Draw handles
        painter.save()
        hc = QColor(Colors.ACCENT_PRIMARY)
        painter.setPen(QPen(hc, 1))
        painter.setBrush(QBrush(hc))
        s = self.HANDLE_SIZE
        for hr in self._handle_rects():
            painter.drawEllipse(hr)
        painter.restore()

    def boundingRect(self) -> QRectF:
        s = self.HANDLE_SIZE
        return self.rect().adjusted(-s, -s, s, s)

    # ── Mouse events ──────────────────────────────────────────────────

    def hoverMoveEvent(self, event) -> None:
        h = self._hit_handle(event.pos())
        if h is not None:
            self.setCursor(QCursor(self._CURSORS[h]))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.scenePos()
            self._rect_at_drag = QRectF(self.rect())
            h = self._hit_handle(event.pos())
            if h is not None:
                self._drag_handle = h
                self._moving = False
            else:
                self._drag_handle = None
                self._moving = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_start is None:
            super().mouseMoveEvent(event)
            return

        delta = event.scenePos() - self._drag_start
        r = QRectF(self._rect_at_drag)
        ir = self._img_rect
        MIN = 20.0  # minimum dimension

        if self._moving:
            # Move whole rect, clamped to image
            r.translate(delta)
            if r.left() < ir.left():
                r.moveLeft(ir.left())
            if r.top() < ir.top():
                r.moveTop(ir.top())
            if r.right() > ir.right():
                r.moveRight(ir.right())
            if r.bottom() > ir.bottom():
                r.moveBottom(ir.bottom())
        else:
            h = self._drag_handle
            # Adjust edges based on which handle
            if h in self._TOP:
                new_top = max(ir.top(), min(r.bottom() - MIN, r.top() + delta.y()))
                r.setTop(new_top)
            if h in self._BOTTOM:
                new_bot = min(ir.bottom(), max(r.top() + MIN, r.bottom() + delta.y()))
                r.setBottom(new_bot)
            if h in self._LEFT:
                new_left = max(ir.left(), min(r.right() - MIN, r.left() + delta.x()))
                r.setLeft(new_left)
            if h in self._RIGHT:
                new_right = min(ir.right(), max(r.left() + MIN, r.right() + delta.x()))
                r.setRight(new_right)

        self.setRect(r)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self._rect_at_drag = None
            self._drag_handle = None
            self._moving = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


# ── Image canvas ──────────────────────────────────────────────────────────────

class ImageCanvas(QGraphicsView):
    """Zoomable, pannable image viewer with overlay support."""

    image_loaded = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    band_clicked = pyqtSignal(object)
    peak_pick_requested = pyqtSignal(float, float)
    crop_requested = pyqtSignal(QRectF)
    lane_border_changed = pyqtSignal(int, float)  # border_idx, new_x

    _MIN_ZOOM = 0.1
    _MAX_ZOOM = 20.0
    _ZOOM_STEP = 1.15

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._zoom_factor = 1.0
        self._lane_overlays: list = []
        self._lane_border_items: list[LaneBorderItem] = []
        self._band_overlays: list = []
        self._hover_overlay: Optional[QGraphicsRectItem] = None
        self._peak_picking_enabled = False
        self._lane_edit_mode = False

        # Crop state
        self._crop_mode = False
        self._crop_start_pos: Optional[QPointF] = None
        self._crop_rect_item: Optional[QGraphicsRectItem] = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet(
            f"QGraphicsView {{ border: 1px solid {Colors.BORDER};"
            f" background-color: {Colors.BG_DARKEST}; }}"
        )

    # ── Image ─────────────────────────────────────────────────────────

    def set_image(self, image: NDArray[np.float64]) -> None:
        self.clear_overlays()
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
        self._scene.clear()
        self._pixmap_item = None
        self._lane_border_items.clear()

        img_uint8 = (np.clip(image, 0, 1) * 255).astype(np.uint8)
        h, w = img_uint8.shape[:2]

        if img_uint8.ndim == 2:
            qimage = QImage(
                img_uint8.tobytes(), w, h, w,
                QImage.Format.Format_Grayscale8,
            )
        else:
            qimage = QImage(
                img_uint8.tobytes(), w, h, 3 * w,
                QImage.Format.Format_RGB888,
            )

        pixmap = QPixmap.fromImage(qimage)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect().toRectF()))

        self._zoom_factor = 1.0
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.image_loaded.emit()

    # ── Lane overlays ─────────────────────────────────────────────────

    def set_lane_edit_mode(self, enabled: bool) -> None:
        """Enable/disable draggable lane borders.

        Should be True only on the lane detection step.
        """
        self._lane_edit_mode = bool(enabled)
        # Rebuild overlays to add/remove border items
        if self._lane_overlays or self._lane_border_items:
            # Redraw with current mode — caller must re-call add_lane_overlays
            pass

    def add_lane_overlays(self, lanes: list[LaneROI]) -> None:
        """Draw lane boundary overlays, with draggable borders in edit mode."""
        self.clear_lane_overlays()
        if not lanes:
            return

        img_h = (
            self._pixmap_item.boundingRect().height()
            if self._pixmap_item else 1000.0
        )
        img_w = (
            self._pixmap_item.boundingRect().width()
            if self._pixmap_item else 1000.0
        )

        colors = Colors.CHART_COLORS

        # Draw lane fill rectangles and labels
        for i, lane in enumerate(lanes):
            color = QColor(colors[i % len(colors)])
            color.setAlpha(30)

            rect = self._scene.addRect(
                lane.x_start, lane.y_start,
                lane.width, lane.height,
                QPen(Qt.PenStyle.NoPen),
                QBrush(color),
            )
            self._lane_overlays.append(rect)

            label = self._scene.addText(str(i + 1))
            label.setDefaultTextColor(QColor(colors[i % len(colors)]))
            label.setPos(lane.center_x - 5, lane.y_start + 5)
            font = label.font()
            font.setPointSize(max(8, min(20, lane.width // 4)))
            font.setBold(True)
            label.setFont(font)
            self._lane_overlays.append(label)

        if self._lane_edit_mode:
            # Collect all internal boundaries (skip leftmost 0 and rightmost w)
            # boundary i splits lane i-1 and lane i
            for i in range(1, len(lanes)):
                x = float(lanes[i].x_start)
                border = LaneBorderItem(
                    border_index=i,
                    x=x,
                    y_top=0.0,
                    y_bottom=float(img_h),
                    canvas=self,
                )
                border._img_width = img_w
                self._scene.addItem(border)
                self._lane_border_items.append(border)

            # Add a hint label at the top
            hint = self._scene.addText("↔ Drag borders to adjust lanes")
            hint.setDefaultTextColor(QColor(Colors.FG_SECONDARY))
            hint.setPos(4, 2)
            font = hint.font()
            font.setPointSize(8)
            hint.setFont(font)
            hint.setZValue(25)
            self._lane_overlays.append(hint)
        else:
            # Static mode — draw solid border lines
            for i, lane in enumerate(lanes):
                border_color = QColor(colors[i % len(colors)])
                pen = QPen(border_color, 2)
                line = self._scene.addLine(
                    lane.x_start, lane.y_start,
                    lane.x_start, lane.y_end,
                    pen,
                )
                self._lane_overlays.append(line)
            # Right edge of last lane
            if lanes:
                last = lanes[-1]
                border_color = QColor(colors[(len(lanes) - 1) % len(colors)])
                pen = QPen(border_color, 2)
                line = self._scene.addLine(
                    last.x_end, last.y_start,
                    last.x_end, last.y_end,
                    pen,
                )
                self._lane_overlays.append(line)

    def get_current_lane_boundaries(self) -> list[float]:
        """Return current x positions of all draggable borders, sorted."""
        return sorted(b.line().x1() for b in self._lane_border_items)

    def clear_lane_overlays(self) -> None:
        for item in self._lane_overlays:
            self._scene.removeItem(item)
        self._lane_overlays.clear()
        for item in self._lane_border_items:
            self._scene.removeItem(item)
        self._lane_border_items.clear()

    # ── Band overlays ─────────────────────────────────────────────────

    def add_band_overlays(self, lanes: list[LaneROI], bands: list) -> None:
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
            item = BandOverlayItem(rect_geom, band, color, self._on_band_toggled)
            self._scene.addItem(item)
            self._band_overlays.append(item)

    def _on_band_toggled(self, band: DetectedBand) -> None:
        self.band_clicked.emit(band)

    def set_band_comparison_slots(self, band_a, band_b) -> None:
        """Update visual slot markers (A/B) — back-compat for 2-slot usage."""
        slot_map = {}
        if band_a is not None:
            slot_map[(band_a.lane_index, band_a.band_index)] = "A"
        if band_b is not None:
            slot_map[(band_b.lane_index, band_b.band_index)] = "B"
        self.set_all_comparison_slots(slot_map)

    def set_all_comparison_slots(self, slot_map: dict) -> None:
        """Update visual markers for all comparison slots.

        Args:
            slot_map: {(lane_index, band_index): color_hex_or_label}
                      Any band not in the map gets its marker cleared.
        """
        for item in self._band_overlays:
            if not isinstance(item, BandOverlayItem):
                continue
            b = item.band
            key = (b.lane_index, b.band_index)
            val = slot_map.get(key)
            if val is not None:
                item.set_comparison_slot(val)
            else:
                item.set_comparison_slot(None)

    def clear_band_overlays(self) -> None:
        for item in self._band_overlays:
            self._scene.removeItem(item)
        self._band_overlays.clear()

    # ── Hover indicator ───────────────────────────────────────────────

    def show_hover_indicator(self, lane: LaneROI, y_position: float) -> None:
        if y_position < 0:
            self.hide_hover_indicator()
            return
        color = QColor(Colors.ACCENT_PRIMARY)
        color.setAlpha(150)
        rect_geom = QRectF(lane.x_start + 2, y_position - 1.5, lane.width - 4, 3)
        if self._hover_overlay is None:
            self._hover_overlay = self._scene.addRect(
                rect_geom, QPen(Qt.PenStyle.NoPen), QBrush(color)
            )
            self._hover_overlay.setZValue(10)
        else:
            self._hover_overlay.setRect(rect_geom)

    def hide_hover_indicator(self) -> None:
        if self._hover_overlay:
            self._scene.removeItem(self._hover_overlay)
            self._hover_overlay = None

    # ── Crop preview ──────────────────────────────────────────────────

    def show_crop_preview(self, rect: QRectF) -> None:
        """Show a resizable crop preview using ResizableCropItem."""
        self.clear_crop_preview()
        img_rect = (
            self._pixmap_item.boundingRect()
            if self._pixmap_item else QRectF(0, 0, 9999, 9999)
        )
        self._crop_rect_item = ResizableCropItem(rect, img_rect)
        self._scene.addItem(self._crop_rect_item)

    def clear_crop_preview(self) -> None:
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None

    def get_current_crop_preview_bounds(self):
        if self._crop_rect_item:
            r = self._crop_rect_item.rect()
            return (int(r.top()), int(r.bottom()), int(r.left()), int(r.right()))
        return None

    # ── Clear all ─────────────────────────────────────────────────────

    def clear_overlays(self) -> None:
        self.clear_lane_overlays()
        self.clear_band_overlays()
        self.hide_hover_indicator()

    # ── Fit to view ───────────────────────────────────────────────────

    def fit_to_view(self) -> None:
        if self._pixmap_item:
            self._zoom_factor = 1.0
            self.resetTransform()
            self.fitInView(
                self._scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio,
            )

    # ── Modes ─────────────────────────────────────────────────────────

    def set_peak_picking_enabled(self, enabled: bool) -> None:
        self._peak_picking_enabled = bool(enabled)

    def set_crop_mode(self, enabled: bool) -> None:
        self._crop_mode = enabled
        if not enabled and self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
            self._crop_start_pos = None

    # ── Events ────────────────────────────────────────────────────────

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

    def mousePressEvent(self, event) -> None:
        # Crop mode
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton:
            self._crop_start_pos = self.mapToScene(event.position().toPoint())
            color = QColor(Colors.ACCENT_PRIMARY)
            pen = QPen(color, 2, Qt.PenStyle.DashLine)
            brush = QColor(color)
            brush.setAlpha(30)
            if self._crop_rect_item is None:
                self._crop_rect_item = self._scene.addRect(
                    QRectF(self._crop_start_pos, self._crop_start_pos), pen, brush
                )
            else:
                self._crop_rect_item.setRect(
                    QRectF(self._crop_start_pos, self._crop_start_pos)
                )
            event.accept()
            return

        # Peak picking
        if (
            self._peak_picking_enabled
            and event.button() == Qt.MouseButton.LeftButton
            and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            pos = self.mapToScene(event.position().toPoint())
            self.peak_pick_requested.emit(float(pos.x()), float(pos.y()))
            event.accept()
            return

        # Pan
        if (
            event.button() == Qt.MouseButton.MiddleButton
            or (
                event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            )
        ):
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            super().mousePressEvent(event)
            return

        # Default — pass to scene items (LaneBorderItem, BandOverlayItem)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._crop_mode and self._crop_start_pos is not None:
            current_pos = self.mapToScene(event.position().toPoint())
            rect = QRectF(self._crop_start_pos, current_pos).normalized()
            if self._pixmap_item:
                rect = rect.intersected(self._pixmap_item.boundingRect())
            if self._crop_rect_item:
                self._crop_rect_item.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._crop_mode and event.button() == Qt.MouseButton.LeftButton:
            if self._crop_rect_item and self._crop_start_pos is not None:
                rect = self._crop_rect_item.rect()
                if rect.width() > 4 and rect.height() > 4:
                    self.crop_requested.emit(rect)
            self._crop_start_pos = None
            event.accept()
            return

        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

        super().mouseReleaseEvent(event)