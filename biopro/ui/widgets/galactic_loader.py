import random
from enum import Enum, auto

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from biopro.ui.theme import Colors, theme_manager


class _Phase(Enum):
    IDLE = auto()
    WARPING_OUT = auto()  # "Arriving at destination" — speed ramps to max
    DONE = auto()  # Warp-out peaked; signal has been emitted


class GalacticLoader(QWidget):
    """A cinematic Galactic hyperspace loading screen.

    Transition flow
    ---------------
    1. set_module()   — resets stars, sets message, begins entry fade-in
    2. warp_out()     — ramps speed to lightspeed; emits warp_out_finished when peak is reached
    3. Caller handles the crossfade externally (workspace_window._crossfade_to_analysis)

    The internal QTimer keeps running through all phases so the animation is never
    interrupted by the page swap.
    """

    # Fired once the warp-out speed peak is reached — caller should start the crossfade.
    warp_out_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self.stars = []
        self._init_stars()

        self.speed = 0.0
        self.target_speed = 0.05
        self.accel = 0.0004

        self._phase = _Phase.IDLE
        # Countdown in ticks once we reach warp-out target speed before emitting signal
        self._warp_out_ticks = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)  # ~60 fps

        self.message = "Initializing Hyperdrive..."
        self.module_name = ""

        self.global_opacity = 0.0
        self.fade_speed = 0.02

        theme_manager.theme_changed.connect(self.update)

    def _init_stars(self):
        self.stars = []
        for _ in range(300):
            self.stars.append(
                {
                    "x": random.uniform(-1.5, 1.5),
                    "y": random.uniform(-1.0, 1.0),
                    "z": random.uniform(0.1, 2.0),
                    "size": random.uniform(1, 2.5),
                }
            )

    def set_module(self, name: str):
        self.module_name = name
        self.message = f"Traveling to {name}..."
        self.speed = 0.0
        self.global_opacity = 0.0
        self._phase = _Phase.IDLE

    def _update_animation(self):
        # 1. Fade in the whole screen
        if self.global_opacity < 1.0:
            self.global_opacity = min(1.0, self.global_opacity + self.fade_speed)

        # 2. Speed management depending on phase
        if self._phase == _Phase.IDLE:
            # Normal cruising ramp
            if self.speed < self.target_speed:
                self.speed += self.accel

        elif self._phase == _Phase.WARPING_OUT:
            # Accelerate hard toward lightspeed
            self.speed += 0.02
            if self.speed >= 0.8:
                self.speed = 0.8
                # Count a few frames at peak so the effect lands visually
                self._warp_out_ticks += 1
                if self._warp_out_ticks >= 4:  # ~64ms of peak warp — brief, cinematic
                    self._phase = _Phase.DONE
                    self.warp_out_finished.emit()

        # _Phase.DONE — keep running at max so crossfade looks great

        # 3. Update stars
        for s in self.stars:
            s["z"] -= self.speed
            if s["z"] <= 0.05:
                s["z"] = 2.0
                s["x"] = random.uniform(-1.5, 1.5)
                s["y"] = random.uniform(-1.0, 1.0)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # 1. Background
        painter.fillRect(self.rect(), QColor(Colors.BG_DARKEST))

        # 2. Theme accent
        is_sw = "Galactic" in theme_manager.current_theme_name
        is_dark_side = is_sw and getattr(Colors, "DNA_PRIMARY", "").upper() == "#E60000"
        accent = Colors.ACCENT_PRIMARY
        if is_sw:
            accent = Colors.ACCENT_PRIMARY if not is_dark_side else Colors.DNA_PRIMARY

        painter.setOpacity(self.global_opacity)

        for s in self.stars:
            px = cx + (s["x"] * w) / s["z"]
            py = cy + (s["y"] * h) / s["z"]

            trail_length = self.speed * 15
            pz_prev = s["z"] + trail_length
            px_prev = cx + (s["x"] * w) / pz_prev
            py_prev = cy + (s["y"] * h) / pz_prev

            z_fade = 1.0 - (s["z"] / 2.0)
            alpha = max(0, min(255, int(255 * z_fade)))

            if self.speed > 0.025:
                base_color = QColor(accent)
                color = QColor(
                    int(base_color.red() * 0.7 + 255 * 0.3),
                    int(base_color.green() * 0.7 + 255 * 0.3),
                    int(base_color.blue() * 0.7 + 255 * 0.3),
                    alpha,
                )
            else:
                color = QColor(255, 255, 255, alpha)

            pen = QPen(color)
            pen.setWidthF(max(0.5, s["size"] * z_fade * 0.8))
            painter.setPen(pen)

            if self.speed > 0.005:
                painter.drawLine(QPointF(px_prev, py_prev), QPointF(px, py))
            else:
                painter.drawPoint(QPointF(px, py))

        # 3. Vignette
        from PyQt6.QtGui import QBrush, QRadialGradient

        vignette = QRadialGradient(cx, cy, max(w, h) * 0.6)
        vignette.setColorAt(0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.7, QColor(0, 0, 0, 40))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 200))
        painter.fillRect(self.rect(), QBrush(vignette))

        # 4. Message text
        painter.setPen(QColor(accent))
        font = QFont("Courier New", 28, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        text_rect = QRectF(0, h * 0.75, w, 60)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.message.upper())

        # 5. Tech sub-text
        painter.setPen(QColor(Colors.FG_SECONDARY))
        painter.setOpacity(self.global_opacity * 0.5)
        painter.setFont(QFont("Courier New", 12))
        coords = f"{random.randint(1000, 9999)}-{random.randint(10, 99)}"
        sector = random.choice(
            ["INNER RIM", "OUTER RIM", "UNKNOWN REGIONS", "CORE WORLDS", "EXPANSION REGION"]
        )
        sub_text = f"COORDINATES: {coords} | SECTOR: {sector} | STATUS: HYPERDRIVE ENGAGED"
        painter.drawText(QRectF(0, h * 0.75 + 60, w, 30), Qt.AlignmentFlag.AlignCenter, sub_text)

    def warp_out(self):
        """Begin the cinematic warp-out sequence.

        The animation accelerates to lightspeed on its own.  When the visual peak
        is reached the ``warp_out_finished`` signal is emitted so the caller can
        start the crossfade — no callback needed.
        """
        self.message = "ARRIVING AT DESTINATION..."
        self._warp_out_ticks = 0
        self._phase = _Phase.WARPING_OUT


if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    loader = GalacticLoader()
    loader.set_module("Flow Cytometry Analysis")
    loader.setWindowTitle("BioPro - Hyperspace Preview")
    loader.resize(1000, 700)
    loader.show()

    sys.exit(app.exec())
