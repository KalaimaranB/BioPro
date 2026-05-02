import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from biopro.ui.theme import Colors, theme_manager

class StarWarsLoader(QWidget):
    """A cinematic Star Wars hyperspace loading screen."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent) # Background is black
        
        self.stars = []
        self._init_stars()
        
        self.speed = 0.0
        self.target_speed = 0.05  # Slightly slower for smoothness
        self.accel = 0.0004       # Much more gradual acceleration
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)
        
        self.message = "Initializing Hyperdrive..."
        self.module_name = ""
        
        # Smooth entry variables
        self.global_opacity = 0.0
        self.fade_speed = 0.02
        
        theme_manager.theme_changed.connect(self.update)

    def _init_stars(self):
        self.stars = []
        for _ in range(300):
            self.stars.append({
                'x': random.uniform(-1.5, 1.5),
                'y': random.uniform(-1.0, 1.0),
                'z': random.uniform(0.1, 2.0),
                'size': random.uniform(1, 2.5)
            })

    def set_module(self, name: str):
        self.module_name = name
        self.message = f"Traveling to {name}..."
        # Reset speed for a fresh jump
        self.speed = 0.0

    def _update_animation(self):
        # 1. Fade in the whole screen
        if self.global_opacity < 1.0:
            self.global_opacity += self.fade_speed
            
        # 2. Accelerate speed more smoothly
        if self.speed < self.target_speed:
            self.speed += self.accel
            
        # 3. Update stars
        for s in self.stars:
            s['z'] -= self.speed
            if s['z'] <= 0.05:
                s['z'] = 2.0
                s['x'] = random.uniform(-1.5, 1.5)
                s['y'] = random.uniform(-1.0, 1.0)
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        
        # 1. Fill dynamic theme background
        painter.fillRect(self.rect(), QColor(Colors.BG_DARKEST))
        
        # 2. Draw Stars / Hyperspace Lines
        is_sw = "Star Wars" in theme_manager.current_theme_name
        is_dark_side = is_sw and getattr(Colors, "DNA_PRIMARY", "").upper() == "#E60000"
        
        accent = Colors.ACCENT_PRIMARY
        if is_sw:
            accent = Colors.ACCENT_PRIMARY if not is_dark_side else Colors.DNA_PRIMARY
            
        # Use global opacity for the fade-in effect
        painter.setOpacity(self.global_opacity)

        for s in self.stars:
            # Perspective projection
            aspect = w / h if h > 0 else 1
            
            px = cx + (s['x'] * w) / s['z']
            py = cy + (s['y'] * h) / s['z']
            
            # Trail for hyperspace effect
            trail_length = self.speed * 15 # Shorter trails for smoothness
            pz_prev = s['z'] + trail_length
            px_prev = cx + (s['x'] * w) / pz_prev
            py_prev = cy + (s['y'] * h) / pz_prev
            
            # alpha based on Z and global fade
            z_fade = 1.0 - (s['z'] / 2.0)
            alpha = int(255 * z_fade)
            alpha = max(0, min(255, alpha))
            
            # Trails color based on theme
            if self.speed > 0.025:
                # Use theme accent with some white blending for that "laser" look
                base_color = QColor(accent)
                color = QColor(
                    int(base_color.red() * 0.7 + 255 * 0.3),
                    int(base_color.green() * 0.7 + 255 * 0.3),
                    int(base_color.blue() * 0.7 + 255 * 0.3),
                    alpha
                )
            else:
                color = QColor(255, 255, 255, alpha)
            
            pen = QPen(color)
            # Thinner lines for a more premium, less 'chunky' feel
            pen.setWidthF(max(0.5, s['size'] * z_fade * 0.8))
            painter.setPen(pen)
            
            if self.speed > 0.005:
                painter.drawLine(QPointF(px_prev, py_prev), QPointF(px, py))
            else:
                painter.drawPoint(QPointF(px, py))

        # --- NEW: Vignette Overlay ---
        # This draws a soft shadow around the edges to focus the eyes on the center
        from PyQt6.QtGui import QRadialGradient, QBrush
        vignette = QRadialGradient(cx, cy, max(w, h) * 0.6)
        vignette.setColorAt(0, QColor(0, 0, 0, 0))       # Clear in center
        vignette.setColorAt(0.7, QColor(0, 0, 0, 40))    # Slight dimming
        vignette.setColorAt(1.0, QColor(0, 0, 0, 200))   # Deep black at edges
        painter.fillRect(self.rect(), QBrush(vignette))

        # Text Layer - Cinematic Star Wars yellow/blue
        painter.setPen(QColor(accent))
        # Use a tech-y font if possible, fallback to Courier
        font = QFont("Courier New", 28, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        
        text_rect = QRectF(0, h * 0.75, w, 60)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.message.upper())
        
        # Subtext / Tech info
        painter.setPen(QColor(Colors.FG_SECONDARY))
        painter.setOpacity(self.global_opacity * 0.5) # Dimmer subtext
        painter.setFont(QFont("Courier New", 12))
        
        # Random seed based on time or just static for the session
        coords = f"{random.randint(1000, 9999)}-{random.randint(10, 99)}"
        sector = random.choice(['INNER RIM', 'OUTER RIM', 'UNKNOWN REGIONS', 'CORE WORLDS', 'EXPANSION REGION'])
        sub_text = f"COORDINATES: {coords} | SECTOR: {sector} | STATUS: HYPERDRIVE ENGAGED"
        
        painter.drawText(QRectF(0, h * 0.75 + 60, w, 30), Qt.AlignmentFlag.AlignCenter, sub_text)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Create the loader
    loader = StarWarsLoader()
    loader.set_module("Flow Cytometry Analysis")
    loader.setWindowTitle("BioPro - Hyperspace Preview")
    loader.resize(1000, 700)
    loader.show()
    
    sys.exit(app.exec())
