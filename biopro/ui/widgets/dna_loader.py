import math
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtWidgets import QWidget
from biopro.ui.theme import Colors

class ProgrammaticLoader(QWidget):
    """A procedural 3D rotating DNA double helix with cellular dust & neon bloom."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180) # Removed fixed size so it can scale!
        self.angle = 0.0
        
        # Generate ambient "cellular dust" particles
        self.particles = []
        for _ in range(25):
            self.particles.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(0, 1),
                'speed': random.uniform(0.002, 0.006),
                'size': random.uniform(1, 3),
                'alpha': random.randint(20, 80)
            })
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)

    def _update_animation(self):
        self.angle += 0.025
        if self.angle >= math.pi * 2:
            self.angle = 0.0
            
        # Float the ambient particles upwards and sway them
        for p in self.particles:
            p['y'] -= p['speed']
            p['x'] += math.sin(self.angle * 4 + p['y'] * 10) * 0.001
            if p['y'] < 0:
                p['y'] = 1.0
                p['x'] = random.uniform(0, 1)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cy, cx = h / 2, w / 2
        
        # 1. Draw cellular dust
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            c = QColor(Colors.ACCENT_PRIMARY)
            c.setAlpha(p['alpha'])
            painter.setBrush(c)
            painter.drawEllipse(QRectF(p['x'] * w, p['y'] * h, p['size'], p['size']))
            
        # Dynamic DNA scale based on the current widget size
        scale = min(w, h) / 180.0
        num_bases, spacing, amplitude, twist = 14, 10 * scale, 45 * scale, 0.45
        start_y = cy - (num_bases * spacing) / 2
        
        # 2. Calculate 3D coordinates
        points = []
        for i in range(num_bases):
            y = start_y + i * spacing
            phase1 = self.angle + (i * twist)
            x1 = cx + math.sin(phase1) * amplitude
            z1 = math.cos(phase1)
            
            phase2 = phase1 + math.pi
            x2 = cx + math.sin(phase2) * amplitude
            z2 = math.cos(phase2)
            points.append({'y': y, 'x1': x1, 'z1': z1, 'x2': x2, 'z2': z2})

        # Base colors: Strand 1 is Teal, Strand 2 is Purple
        c_strand1 = QColor(Colors.ACCENT_PRIMARY)
        c_strand2 = QColor("#a371f7") # A nice bio-purple

        # 3. Draw Pass 1: The Back Nodes (z < 0)
        painter.setPen(Qt.PenStyle.NoPen)
        for p in points:
            s1, s2 = (5 + p['z1']*2.5) * scale, (5 + p['z2']*2.5) * scale
            if p['z1'] < 0:
                c = QColor(c_strand1); c.setAlpha(80)
                painter.setBrush(c)
                painter.drawEllipse(QRectF(p['x1']-s1/2, p['y']-s1/2, s1, s1))
            if p['z2'] < 0:
                c = QColor(c_strand2); c.setAlpha(80)
                painter.setBrush(c)
                painter.drawEllipse(QRectF(p['x2']-s2/2, p['y']-s2/2, s2, s2))

        # 4. Draw Pass 2: The Hydrogen Bonds (Gradient)
        for p in points:
            pen = QPen()
            pen.setWidthF(max(1.0, 2.0 * scale))
            grad = QLinearGradient(p['x1'], p['y'], p['x2'], p['y'])
            
            c_bond1 = QColor(c_strand1); c_bond1.setAlpha(int(120 + p['z1']*80))
            c_bond2 = QColor(c_strand2); c_bond2.setAlpha(int(120 + p['z2']*80))
            grad.setColorAt(0.0, c_bond1)
            grad.setColorAt(1.0, c_bond2)
            
            pen.setBrush(QBrush(grad))
            painter.setPen(pen)
            painter.drawLine(QPointF(p['x1'], p['y']), QPointF(p['x2'], p['y']))

        # 5. Draw Pass 3: The Front Nodes (z >= 0) with Neon Bloom
        painter.setPen(Qt.PenStyle.NoPen)
        for p in points:
            s1, s2 = (5 + p['z1']*2.5) * scale, (5 + p['z2']*2.5) * scale
            if p['z1'] >= 0:
                glow = QColor(c_strand1); glow.setAlpha(40) # Neon bloom
                painter.setBrush(glow)
                painter.drawEllipse(QRectF(p['x1']-s1, p['y']-s1, s1*2, s1*2))
                
                core = QColor(c_strand1); core.setAlpha(255)
                painter.setBrush(core)
                painter.drawEllipse(QRectF(p['x1']-s1/2, p['y']-s1/2, s1, s1))
            if p['z2'] >= 0:
                glow = QColor(c_strand2); glow.setAlpha(40) # Neon bloom
                painter.setBrush(glow)
                painter.drawEllipse(QRectF(p['x2']-s2, p['y']-s2, s2*2, s2*2))
                
                core = QColor(c_strand2); core.setAlpha(255)
                painter.setBrush(core)
                painter.drawEllipse(QRectF(p['x2']-s2/2, p['y']-s2/2, s2, s2))