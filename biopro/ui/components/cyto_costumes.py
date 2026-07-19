import math
import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsRectItem,
)


def _tapered_ribbon(points, widths):
    """Build a closed, width-varying ribbon path from a centerline.

    ``points`` is a list of (x, y) tuples describing the centerline and
    ``widths`` gives the half-width at each corresponding point (values
    near 0 taper the ribbon to a point). This reads far more like flowing
    water/air than a single stroked line, since the shape can bulge and
    taper the way a real current would.
    """
    if len(points) < 2:
        return QPainterPath()
    top_pts, bot_pts = [], []
    n = len(points)
    for i in range(n):
        x, y = points[i]
        if i == 0:
            dx, dy = points[i + 1][0] - x, points[i + 1][1] - y
        elif i == n - 1:
            dx, dy = x - points[i - 1][0], y - points[i - 1][1]
        else:
            dx, dy = points[i + 1][0] - points[i - 1][0], points[i + 1][1] - points[i - 1][1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length
        w = widths[i]
        top_pts.append((x + nx * w, y + ny * w))
        bot_pts.append((x - nx * w, y - ny * w))
    path = QPainterPath()
    path.moveTo(*top_pts[0])
    for pt in top_pts[1:]:
        path.lineTo(*pt)
    for pt in reversed(bot_pts):
        path.lineTo(*pt)
    path.closeSubpath()
    return path


class CytoCostume:
    """Base interface for Cyto's theme-dependent accessories/costumes."""

    def attach(self, cyto_widget):
        pass

    def detach(self, cyto_widget):
        pass

    def animate(self, cyto_widget, time_step: float):
        pass


class GalacticCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.glow_effect = None

    def attach(self, cyto_widget):
        self.handle = QGraphicsRectItem(45, -20, 10, 35)
        handle_grad = QLinearGradient(45, -20, 55, -20)
        handle_grad.setColorAt(0, QColor("#8b949e"))
        handle_grad.setColorAt(1, QColor("#c9d1d9"))
        self.handle.setBrush(QBrush(handle_grad))
        self.handle.setPen(QPen(QColor("#ffffff"), 1))
        self.handle.setParentItem(cyto_widget.right_arm)
        self.items.append(self.handle)

        self.blade = QGraphicsRectItem(47, -100, 6, 80)
        self.blade.setBrush(QBrush(QColor("#ffffff")))
        self.blade.setPen(QPen(Qt.PenStyle.NoPen))
        self.blade.setParentItem(cyto_widget.right_arm)
        self.items.append(self.blade)

        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setOffset(0, 0)
        theme_name = (
            cyto_widget.theme_manager.current_theme_name.lower()
            if hasattr(cyto_widget, "theme_manager")
            else ""
        )
        if "dark" in theme_name or "imperial" in theme_name:
            glow_color = QColor(255, 0, 0)
        elif "light" in theme_name:
            glow_color = QColor(0, 150, 255)
        else:
            glow_color = QColor(57, 255, 20)

        self.glow_effect.setColor(glow_color)
        self.glow_effect.setBlurRadius(20)
        self.blade.setGraphicsEffect(self.glow_effect)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget, time_step: float):
        if self.glow_effect:
            hum_blur = 20 + math.sin(time_step * 15) * 6
            self.glow_effect.setBlurRadius(hum_blur)


class MandalorianCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.electric_arc = None

    def attach(self, cyto_widget):
        self.helmet = QGraphicsPathItem()
        path = QPainterPath()
        path.moveTo(-25, 0)
        path.lineTo(-25, -25)
        path.cubicTo(-25, -48, 25, -48, 25, -25)
        path.lineTo(25, 0)
        path.lineTo(15, 0)
        path.lineTo(8, 22)
        path.lineTo(-8, 22)
        path.lineTo(-15, 0)
        path.closeSubpath()
        self.helmet.setPath(path)

        # Opaque Beskar metal
        grad = QLinearGradient(-25, -48, 25, 22)
        grad.setColorAt(0, QColor("#ffffff"))
        grad.setColorAt(0.2, QColor("#cccccc"))
        grad.setColorAt(0.8, QColor("#888888"))
        grad.setColorAt(1, QColor("#444444"))
        self.helmet.setBrush(QBrush(grad))
        self.helmet.setPen(QPen(QColor("#111111"), 2))

        helmet_glow = QGraphicsDropShadowEffect()
        helmet_glow.setBlurRadius(15)
        helmet_glow.setColor(QColor(0, 0, 0, 150))
        helmet_glow.setOffset(0, 3)
        self.helmet.setGraphicsEffect(helmet_glow)

        self.helmet.setParentItem(cyto_widget.cyto_group)
        self.helmet.setZValue(5)
        self.items.append(self.helmet)

        self.visor = QGraphicsPathItem()
        v_path = QPainterPath()
        v_path.moveTo(-16, -10)
        v_path.lineTo(16, -10)
        v_path.lineTo(16, -2)
        v_path.lineTo(5, -2)
        v_path.lineTo(4, 18)
        v_path.lineTo(-4, 18)
        v_path.lineTo(-5, -2)
        v_path.lineTo(-16, -2)
        v_path.closeSubpath()
        self.visor.setPath(v_path)
        self.visor.setBrush(QBrush(QColor("#000000")))
        self.visor.setPen(QPen(QColor("#111111"), 1))
        self.visor.setParentItem(cyto_widget.cyto_group)
        self.visor.setZValue(5.1)
        self.items.append(self.visor)

        cyto_widget.left_eye.setOpacity(0)
        cyto_widget.right_eye.setOpacity(0)
        cyto_widget.mouth.setOpacity(0)
        cyto_widget.core.setOpacity(0)

        # Blaster pointing forward (horizontal) — kept close to the hand so
        # it reads as held, not floating off on its own.
        self.stock = QGraphicsPathItem()
        s_path = QPainterPath()
        s_path.moveTo(35, -5)
        s_path.lineTo(48, -5)
        s_path.lineTo(48, 5)
        s_path.lineTo(30, 5)
        s_path.closeSubpath()
        self.stock.setPath(s_path)

        tech_grad = QLinearGradient(30, -5, 48, 5)
        tech_grad.setColorAt(0, QColor("#1f6feb"))
        tech_grad.setColorAt(1, QColor("#010409"))
        self.stock.setBrush(QBrush(tech_grad))
        self.stock.setPen(QPen(QColor("#79c0ff"), 1.5))
        self.stock.setParentItem(cyto_widget.right_arm)
        self.items.append(self.stock)

        self.barrel = QGraphicsRectItem(48, -3, 30, 4)
        metal_grad = QLinearGradient(48, -3, 48, 1)
        metal_grad.setColorAt(0, QColor("#c9d1d9"))
        metal_grad.setColorAt(1, QColor("#484f58"))
        self.barrel.setBrush(QBrush(metal_grad))
        self.barrel.setParentItem(cyto_widget.right_arm)
        self.items.append(self.barrel)

        self.scope = QGraphicsRectItem(54, -8, 15, 3)
        self.scope.setBrush(QBrush(QColor("#161b22")))
        self.scope.setParentItem(cyto_widget.right_arm)
        self.items.append(self.scope)

        self.fork1 = QGraphicsRectItem(78, -6, 7, 2)
        self.fork1.setBrush(QBrush(metal_grad))
        self.fork1.setParentItem(cyto_widget.right_arm)
        self.items.append(self.fork1)

        self.fork2 = QGraphicsRectItem(78, 2, 7, 2)
        self.fork2.setBrush(QBrush(metal_grad))
        self.fork2.setParentItem(cyto_widget.right_arm)
        self.items.append(self.fork2)

        self.electric_arc = QGraphicsPathItem()
        self.electric_arc.setPen(QPen(QColor(57, 255, 20), 1.5))
        self.electric_arc.setParentItem(cyto_widget.right_arm)
        arc_glow = QGraphicsDropShadowEffect()
        arc_glow.setBlurRadius(10)
        arc_glow.setColor(QColor(57, 255, 20))
        arc_glow.setOffset(0, 0)
        self.electric_arc.setGraphicsEffect(arc_glow)
        self.items.append(self.electric_arc)

    def detach(self, cyto_widget):
        cyto_widget.left_eye.setOpacity(1)
        cyto_widget.right_eye.setOpacity(1)
        cyto_widget.mouth.setOpacity(1)
        cyto_widget.core.setOpacity(1)
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget, time_step: float):
        if self.electric_arc:
            path = QPainterPath()
            path.moveTo(80, -5)
            if random.random() > 0.4:
                y = -5
                for _i in range(1, 4):
                    y += 2
                    x = 80 + random.uniform(-2, 2)
                    path.lineTo(x, y)
                path.lineTo(80, 3)
                self.electric_arc.setOpacity(1)
            else:
                self.electric_arc.setOpacity(0)
            self.electric_arc.setPath(path)


class TriStateCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.hat_group = None
        self.lens_glow = None

    def attach(self, cyto_widget):
        self.hat_group = QGraphicsItemGroup()
        self.hat_group.setParentItem(cyto_widget.cyto_group)
        self.hat_group.setZValue(6)
        self.items.append(self.hat_group)

        self.brim = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(-50, -42)
        b_path.quadTo(0, -55, 50, -42)
        b_path.quadTo(0, -47, -50, -42)
        self.brim.setPath(b_path)

        fedora_grad = QLinearGradient(-50, -80, 50, -40)
        fedora_grad.setColorAt(0, QColor(0, 168, 150, 230))
        fedora_grad.setColorAt(1, QColor(0, 80, 72, 230))

        self.brim.setBrush(QBrush(fedora_grad))
        self.brim.setPen(QPen(QColor("#00a896"), 2))
        self.brim.setParentItem(self.hat_group)

        self.crown = QGraphicsPathItem()
        c_path = QPainterPath()
        c_path.moveTo(-30, -50)
        c_path.lineTo(-25, -80)
        c_path.quadTo(0, -70, 25, -80)
        c_path.lineTo(30, -50)
        c_path.closeSubpath()
        self.crown.setPath(c_path)
        self.crown.setBrush(QBrush(fedora_grad))
        self.crown.setPen(QPen(QColor("#00a896"), 2))
        self.crown.setParentItem(self.hat_group)

        self.band = QGraphicsPathItem()
        band_path = QPainterPath()
        band_path.moveTo(-31, -48)
        band_path.lineTo(-28, -58)
        band_path.quadTo(0, -63, 28, -58)
        band_path.lineTo(31, -48)
        band_path.quadTo(0, -53, -31, -48)
        self.band.setPath(band_path)
        self.band.setBrush(QBrush(QColor("#010409")))
        self.band.setParentItem(self.hat_group)

        self.buckle = QGraphicsRectItem(-5, -60, 10, 8)
        self.buckle.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.buckle.setPen(QPen(QColor("#ffcc00"), 2))
        self.buckle.setParentItem(self.hat_group)

        hat_glow = QGraphicsDropShadowEffect()
        hat_glow.setBlurRadius(15)
        hat_glow.setColor(QColor("#00a896"))
        hat_glow.setOffset(0, 0)
        self.crown.setGraphicsEffect(hat_glow)

        # Detective's magnifying glass — pairs with the fedora and still
        # works as Cyto's UI pointer. Drawn as an angled rod running up to
        # a glass-tinted lens, sized and positioned close to the hand so it
        # reads as held rather than floating beside the arm.
        self.handle = QGraphicsPathItem()
        h_path = QPainterPath()
        h_path.moveTo(38, 8)
        h_path.lineTo(45, 14)
        h_path.lineTo(73, -27)
        h_path.lineTo(66, -33)
        h_path.closeSubpath()
        self.handle.setPath(h_path)
        handle_grad = QLinearGradient(38, 8, 73, -27)
        handle_grad.setColorAt(0, QColor("#5c3a21"))
        handle_grad.setColorAt(1, QColor("#8b5a2b"))
        self.handle.setBrush(QBrush(handle_grad))
        self.handle.setPen(QPen(QColor("#3d2615"), 1))
        self.handle.setParentItem(cyto_widget.right_arm)
        self.items.append(self.handle)

        self.lens = QGraphicsEllipseItem(55, -59, 34, 34)
        lens_grad = QRadialGradient(72, -42, 20)
        lens_grad.setColorAt(0, QColor(255, 255, 255, 180))
        lens_grad.setColorAt(0.55, QColor(190, 235, 230, 100))
        lens_grad.setColorAt(1, QColor(0, 168, 150, 60))
        self.lens.setBrush(QBrush(lens_grad))
        self.lens.setPen(QPen(QColor("#00a896"), 3))
        self.lens.setParentItem(cyto_widget.right_arm)
        self.items.append(self.lens)

        self.rim_screw = QGraphicsEllipseItem(69, -32, 5, 5)
        self.rim_screw.setBrush(QBrush(QColor("#ffcc00")))
        self.rim_screw.setPen(QPen(QColor("#3d2615"), 1))
        self.rim_screw.setParentItem(cyto_widget.right_arm)
        self.items.append(self.rim_screw)

        self.lens_glow = QGraphicsDropShadowEffect()
        self.lens_glow.setBlurRadius(12)
        self.lens_glow.setColor(QColor("#00a896"))
        self.lens_glow.setOffset(0, 0)
        self.lens.setGraphicsEffect(self.lens_glow)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget, time_step: float):
        if self.hat_group:
            angle = math.sin(time_step) * 5
            self.hat_group.setRotation(angle)
        if self.lens_glow:
            self.lens_glow.setBlurRadius(12 + math.sin(time_step * 3) * 4)


class SubcavernCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.glow_effect = None

    def attach(self, cyto_widget):
        # Blaster pointing forward (horizontal)
        self.body = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(35, -8)
        b_path.lineTo(65, -8)
        b_path.lineTo(65, 8)
        b_path.lineTo(40, 8)
        b_path.lineTo(35, 3)
        b_path.closeSubpath()
        self.body.setPath(b_path)

        grad = QLinearGradient(35, -8, 65, 8)
        grad.setColorAt(0, QColor("#e0e0e0"))
        grad.setColorAt(1, QColor("#666666"))
        self.body.setBrush(QBrush(grad))
        self.body.setPen(QPen(QColor("#333333"), 1.5))
        self.body.setParentItem(cyto_widget.right_arm)
        self.items.append(self.body)

        self.barrel = QGraphicsRectItem(65, -3, 20, 6)
        b_grad = QLinearGradient(65, -3, 65, 3)
        b_grad.setColorAt(0, QColor("#ffaa00"))
        b_grad.setColorAt(1, QColor("#cc5500"))
        self.barrel.setBrush(QBrush(b_grad))
        self.barrel.setParentItem(cyto_widget.right_arm)
        self.items.append(self.barrel)

        self.chamber = QGraphicsEllipseItem(46, -6, 12, 12)
        c_grad = QRadialGradient(52, 0, 6)
        c_grad.setColorAt(0, QColor(0, 255, 255, 150))
        c_grad.setColorAt(1, QColor(0, 100, 200, 200))
        self.chamber.setBrush(QBrush(c_grad))
        self.chamber.setPen(QPen(QColor("#00ffff"), 1))
        self.chamber.setParentItem(cyto_widget.right_arm)
        self.items.append(self.chamber)

        self.slug = QGraphicsPathItem()
        s_path = QPainterPath()
        s_path.moveTo(48, 0)
        s_path.quadTo(52, -4, 56, 0)
        s_path.lineTo(56, 2)
        s_path.quadTo(52, 4, 48, 2)
        s_path.closeSubpath()
        self.slug.setPath(s_path)
        self.slug.setBrush(QBrush(QColor("#ff5500")))
        self.slug.setParentItem(cyto_widget.right_arm)
        self.slug.setZValue(1)
        self.items.append(self.slug)

        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setColor(QColor(0, 255, 255))
        self.glow_effect.setBlurRadius(15)
        self.glow_effect.setOffset(0, 0)
        self.chamber.setGraphicsEffect(self.glow_effect)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget, time_step: float):
        if self.glow_effect:
            radius = 15 + math.sin(time_step * 8) * 5
            self.glow_effect.setBlurRadius(radius)


class NinjagoCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.tornado_layers = []

    def attach(self, cyto_widget):
        self.mask_group = QGraphicsItemGroup()
        self.mask_group.setParentItem(cyto_widget.cyto_group)
        self.mask_group.setZValue(5.5)
        self.items.append(self.mask_group)

        red_grad = QLinearGradient(-25, -40, 25, 0)
        red_grad.setColorAt(0, QColor("#d32f2f"))
        red_grad.setColorAt(1, QColor("#8e0000"))

        top = QGraphicsPathItem()
        t_path = QPainterPath()
        t_path.moveTo(-25, -15)
        t_path.quadTo(0, -45, 25, -15)
        t_path.quadTo(0, -25, -25, -15)
        top.setPath(t_path)
        top.setBrush(QBrush(red_grad))
        top.setParentItem(self.mask_group)

        bot = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(-22, -5)
        b_path.quadTo(0, 25, 22, -5)
        b_path.quadTo(0, 5, -22, -5)
        bot.setPath(b_path)
        bot.setBrush(QBrush(red_grad))
        bot.setParentItem(self.mask_group)

        emblem = QGraphicsPathItem()
        e_path = QPainterPath()
        e_path.moveTo(0, -32)
        e_path.lineTo(4, -28)
        e_path.lineTo(0, -24)
        e_path.lineTo(-4, -28)
        e_path.closeSubpath()
        emblem.setPath(e_path)
        emblem.setBrush(QBrush(QColor("#ffd700")))
        emblem.setParentItem(self.mask_group)

        cyto_widget.left_eye.setRect(-18, -15, 12, 10)
        cyto_widget.right_eye.setRect(6, -15, 12, 10)
        cyto_widget.mouth.setOpacity(0)

        # Spinjitzu vortex — a tight funnel that hugs the body (wide at the
        # feet, narrow overhead) built from smoothed curves instead of a
        # sprawling jagged polyline that used to reach off past the dialog.
        for i in range(3):
            layer = QGraphicsPathItem()
            layer.setParentItem(cyto_widget.cyto_group)
            layer.setZValue(-1 + i * 0.1)

            glow = QGraphicsDropShadowEffect()
            glow.setOffset(0, 0)
            glow.setBlurRadius(14)
            if i % 2 == 0:
                layer.setPen(
                    QPen(
                        QColor(255, 120, 0, 210), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
                    )
                )
                glow.setColor(QColor(255, 100, 0))
            else:
                layer.setPen(
                    QPen(
                        QColor(255, 205, 60, 210), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
                    )
                )
                glow.setColor(QColor(255, 200, 0))

            layer.setGraphicsEffect(glow)
            self.tornado_layers.append(layer)
            self.items.append(layer)

    def detach(self, cyto_widget):
        cyto_widget.mouth.setOpacity(1)
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.tornado_layers.clear()

    def animate(self, cyto_widget, time_step: float):
        base_y, top_y = 34, -58
        turns, segments = 2.2, 22
        layer_count = max(len(self.tornado_layers), 1)
        for i, layer in enumerate(self.tornado_layers):
            path = QPainterPath()
            phase = time_step * 6 + i * (2 * math.pi / layer_count)
            prev = None
            for s in range(segments + 1):
                frac = s / segments
                y = base_y + (top_y - base_y) * frac
                radius = 6 + (1 - frac) * 26
                angle = phase + frac * turns * 2 * math.pi
                x = math.cos(angle) * radius
                if prev is None:
                    path.moveTo(x, y)
                else:
                    mid_x, mid_y = (prev[0] + x) / 2, (prev[1] + y) / 2
                    path.quadTo(prev[0], prev[1], mid_x, mid_y)
                prev = (x, y)
            layer.setPath(path)


class AvatarAangCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.swirl_group = None

    def attach(self, cyto_widget):
        self.arrow = QGraphicsPathItem()
        path = QPainterPath()
        path.moveTo(0, -30)
        path.lineTo(5, -20)
        path.lineTo(2, -20)
        path.lineTo(2, -10)
        path.lineTo(-2, -10)
        path.lineTo(-2, -20)
        path.lineTo(-5, -20)
        path.closeSubpath()
        self.arrow.setPath(path)
        self.arrow.setBrush(QBrush(QColor(135, 206, 235)))
        self.arrow.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrow.setParentItem(cyto_widget.cyto_group)
        self.arrow.setZValue(6)

        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(QColor(135, 206, 235))
        glow.setOffset(0, 0)
        self.arrow.setGraphicsEffect(glow)
        self.items.append(self.arrow)

        self.staff = QGraphicsRectItem(45, -60, 4, 90)
        s_grad = QLinearGradient(45, 0, 49, 0)
        s_grad.setColorAt(0, QColor("#a67c52"))
        s_grad.setColorAt(1, QColor("#593e26"))
        self.staff.setBrush(QBrush(s_grad))
        self.staff.setParentItem(cyto_widget.right_arm)
        self.items.append(self.staff)

        # Glider wings — closed leaf shapes (two quadratic curves meeting
        # at both tips) instead of the old open path, which Qt was filling
        # by silently straight-lining the gap and rendering as a stray shard.
        self.wing1 = QGraphicsPathItem()
        w1_path = QPainterPath()
        w1_path.moveTo(45, -52)
        w1_path.quadTo(29, -44, 45, -35)
        w1_path.quadTo(37, -44, 45, -52)
        w1_path.closeSubpath()
        self.wing1.setPath(w1_path)
        wing_grad1 = QLinearGradient(29, -52, 45, -35)
        wing_grad1.setColorAt(0, QColor("#ffb703"))
        wing_grad1.setColorAt(1, QColor("#ff8c00"))
        self.wing1.setBrush(QBrush(wing_grad1))
        self.wing1.setPen(QPen(QColor("#c96f00"), 1))
        self.wing1.setParentItem(cyto_widget.right_arm)
        self.items.append(self.wing1)

        self.wing2 = QGraphicsPathItem()
        w2_path = QPainterPath()
        w2_path.moveTo(49, -52)
        w2_path.quadTo(65, -44, 49, -35)
        w2_path.quadTo(57, -44, 49, -52)
        w2_path.closeSubpath()
        self.wing2.setPath(w2_path)
        wing_grad2 = QLinearGradient(49, -52, 65, -35)
        wing_grad2.setColorAt(0, QColor("#ffb703"))
        wing_grad2.setColorAt(1, QColor("#ff8c00"))
        self.wing2.setBrush(QBrush(wing_grad2))
        self.wing2.setPen(QPen(QColor("#c96f00"), 1))
        self.wing2.setParentItem(cyto_widget.right_arm)
        self.items.append(self.wing2)

        # Airbending swirl — a spinning triskelion at the staff's tip that
        # echoes the Air Nomad emblem, replacing the old loose cubic
        # squiggles that sprawled up past the character's head.
        self.swirl_group = QGraphicsItemGroup()
        self.swirl_group.setParentItem(cyto_widget.right_arm)
        self.swirl_group.setPos(47, -68)
        self.swirl_group.setZValue(2)
        self.items.append(self.swirl_group)

        swirl_pen = QPen(
            QColor(255, 255, 255, 210), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
        )
        for arm_i in range(3):
            blade = QGraphicsPathItem()
            b_path = QPainterPath()
            segments = 14
            for s in range(segments + 1):
                frac = s / segments
                r = 4 + frac * 15
                theta = arm_i * (2 * math.pi / 3) + frac * 2.3
                x = math.cos(theta) * r
                y = math.sin(theta) * r
                if s == 0:
                    b_path.moveTo(x, y)
                else:
                    b_path.lineTo(x, y)
            blade.setPath(b_path)
            blade.setPen(swirl_pen)
            blade.setParentItem(self.swirl_group)

        swirl_glow = QGraphicsDropShadowEffect()
        swirl_glow.setBlurRadius(12)
        swirl_glow.setColor(QColor(135, 206, 235))
        swirl_glow.setOffset(0, 0)
        self.swirl_group.setGraphicsEffect(swirl_glow)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.swirl_group = None

    def animate(self, cyto_widget, time_step: float):
        if self.swirl_group:
            self.swirl_group.setRotation((time_step * 140) % 360)
            pulse = 1.0 + math.sin(time_step * 4) * 0.08
            self.swirl_group.setScale(pulse)


class AvatarKorraCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.water_streams = []

    def attach(self, cyto_widget):
        for _i in range(2):
            stream = QGraphicsPathItem()

            grad = QLinearGradient(20, 10, 20, -60)
            grad.setColorAt(0, QColor(0, 130, 255, 50))
            grad.setColorAt(0.5, QColor(70, 205, 255, 190))
            grad.setColorAt(1, QColor(190, 245, 255, 80))
            stream.setBrush(QBrush(grad))
            stream.setPen(QPen(QColor(160, 235, 255, 150), 1))

            glow = QGraphicsDropShadowEffect()
            glow.setBlurRadius(14)
            glow.setColor(QColor(0, 160, 255))
            glow.setOffset(0, 0)
            stream.setGraphicsEffect(glow)

            stream.setParentItem(cyto_widget.right_arm)
            self.items.append(stream)
            self.water_streams.append(stream)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.water_streams.clear()

    def animate(self, cyto_widget, time_step: float):
        # A tapered, filled ribbon (built by _tapered_ribbon) instead of a
        # thin stroked cubic — it bulges and tapers the way a real water
        # tendril would, and stays close to the hand instead of drifting
        # off above the character.
        segments = 14
        for i, stream in enumerate(self.water_streams):
            t = time_step * 2.4 + i * math.pi
            cx, cy = 45, -14
            reach = 46
            pts, widths = [], []
            for s in range(segments + 1):
                frac = s / segments
                y = cy - frac * reach
                taper = 1 - abs(frac - 0.5) * 1.3
                wobble = math.sin(t + frac * 5.5) * 9 * max(taper, 0.15)
                x = cx + wobble
                pts.append((x, y))
                widths.append(math.sin(frac * math.pi) * 5.5 + 0.6)
            stream.setPath(_tapered_ribbon(pts, widths))


class DefaultCostume(CytoCostume):
    def __init__(self):
        self.items = []

    def attach(self, cyto_widget):
        self.pointer = QGraphicsRectItem(45, -20, 4, 30)
        self.pointer.setBrush(QBrush(QColor("#79c0ff")))
        self.pointer.setParentItem(cyto_widget.right_arm)
        self.items.append(self.pointer)

    def detach(self, cyto_widget):
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()


class CostumeFactory:
    @staticmethod
    def get_costume(theme_name: str) -> CytoCostume:
        name = theme_name.lower()
        if "galactic" in name:
            return GalacticCostume()
        elif "guild tracker" in name or "mandalorian" in name:
            return MandalorianCostume()
        elif "tri-state" in name or "innovation" in name:
            return TriStateCostume()
        elif "subcavern" in name or "slugterra" in name:
            return SubcavernCostume()
        elif "vortex kinetics" in name or "ninjago" in name:
            return NinjagoCostume()
        elif "aeroflow" in name or "zen" in name or "aang" in name:
            return AvatarAangCostume()
        elif "hydroflow" in name or "polar" in name or "korra" in name:
            return AvatarKorraCostume()
        else:
            return DefaultCostume()
