"""UI Overlays."""

import math

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class BioLoadingOverlay(QWidget):
    """A universal, translucent loader overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setParent(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.setStyleSheet("background-color: rgba(15, 23, 42, 220);")

        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)

        layout = QVBoxLayout(self)
        from biopro.ui.theme import Colors

        self.lbl_text = QLabel("Loading...")
        self.lbl_text.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; font-size: 18px; font-weight: bold; background: transparent;"
        )
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(self.lbl_text)
        layout.addStretch()

    def set_text(self, text):
        self.lbl_text.setText(text)

    def start(self):
        if self.parent():
            self.resize(self.parent().size())
        self.show()
        self.raise_()
        self.timer.start(40)

    def stop(self):
        self.timer.stop()
        self.hide()

    def _animate(self):
        self.phase += 0.15
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from biopro.ui.theme import Colors

        # Explicitly draw the dark overlay background using the theme's background color
        bg = QColor(Colors.BG_DARKER)
        bg.setAlpha(220)
        painter.fillRect(self.rect(), bg)

        cx = self.width() / 2
        cy = self.height() / 2 - 40

        nucleus_r = 25 + math.sin(self.phase) * 4
        membrane_r = 45 + math.cos(self.phase * 0.7) * 8

        painter.setPen(Qt.PenStyle.NoPen)

        from biopro.ui.theme import Colors

        accent = QColor(Colors.ACCENT_PRIMARY)

        # Draw translucent outer membrane
        accent.setAlpha(60)
        painter.setBrush(QBrush(accent))
        painter.drawEllipse(
            QRectF(cx - membrane_r, cy - membrane_r, membrane_r * 2, membrane_r * 2)
        )

        # Draw solid inner nucleus
        accent.setAlpha(200)
        painter.setBrush(QBrush(accent))
        painter.drawEllipse(QRectF(cx - nucleus_r, cy - nucleus_r, nucleus_r * 2, nucleus_r * 2))

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)
