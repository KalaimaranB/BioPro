from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QLinearGradient
from biopro.ui.theme import Colors

class HologramEffect(QWidget):
    """A high-tech holographic overlay with moving scanlines and a scan beam."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self._offset = 0
        self._beam_x = 0
        self._flicker = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start(30)  # Faster for smoother beam
        
    def _update_animation(self):
        # 1. Update horizontal scanlines
        self._offset = (self._offset + 1) % 20
        
        # 2. Update vertical scan beam
        self._beam_x += 10
        if self._beam_x > self.width():
            self._beam_x = -50
            
        # 3. Subtle flicker
        import random
        if random.random() > 0.95:
            self._flicker = random.uniform(0.7, 1.0)
        else:
            self._flicker = 1.0
            
        self.update()

    def paintEvent(self, event):
        if Colors.SCANLINE_OPACITY <= 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._flicker)
        
        w, h = self.width(), self.height()
        opacity = int(255 * Colors.SCANLINE_OPACITY)
        
        # 1. Draw Horizontal Scanlines
        painter.setPen(Qt.PenStyle.NoPen)
        line_color = QColor(Colors.ACCENT_PRIMARY)
        line_color.setAlpha(opacity)
        
        for y in range(self._offset, h, 8):
            painter.fillRect(0, y, w, 1, line_color)
            
        # 2. Draw Vertical Scan Beam (the "Tactical Scanner")
        if self._beam_x >= 0:
            beam_grad = QLinearGradient(self._beam_x, 0, self._beam_x + 50, 0)
            beam_color = QColor(Colors.ACCENT_PRIMARY)
            beam_color.setAlpha(int(opacity * 2.5)) # Brighter beam
            
            beam_grad.setColorAt(0, QColor(0, 0, 0, 0))
            beam_grad.setColorAt(0.5, beam_color)
            beam_grad.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.fillRect(self._beam_x, 0, 50, h, beam_grad)

        # 3. Add a soft vertical gradient for depth
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor(0, 0, 0, 30))
        gradient.setColorAt(0.5, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 30))
        painter.fillRect(self.rect(), gradient)
