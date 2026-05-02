import math
import random
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QPainterPath

class GroguAI(QWidget):
    """A programmatically drawn, animated Grogu AI character.
    
    This widget uses the QPainter API to render a vector-based character 
    with fluid animations (breathing, blinking, floating, ear twitching).
    It is used as the visual representation of the BioPro AI Assistant.

    Animations:
        - Floating: Sinusoidal Y-translation.
        - Blinking: Randomly triggered eye-lid clipping.
        - Ear Twitch: Randomly triggered rotation offsets.
        - Force Ball: Pulsing radial gradient with float animation.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)
        
        self.phase = 0.0
        self.float_y = 0.0
        self.blink_phase = 1.0  
        self.is_blinking = False
        
        self.ear_twitch = 0.0
        self._target_ear_twitch = 0.0
        
        self.head_tilt = 0.0
        self._target_head_tilt = 0.0
        
        self.force_phase = 0.0
        
        self.skin_base = QColor("#8AA894")      
        self.skin_light = QColor("#ADC7B6") 
        self.skin_shadow = QColor("#5A7363")    
        self.skin_deep = QColor("#2F4235")    
        
        self.ear_inner = QColor("#D4B1AF")      
        self.ear_deep = QColor("#8A5050")       
        
        self.robe_base = QColor("#A39E8F")      
        self.robe_shadow = QColor("#59554A")    
        self.robe_light = QColor("#C2BEB1") 
        
        self.fleece = QColor("#B5B0A1")
        
        self.eye_base = QColor("#050505")       
        self.eye_rim = QColor("#362211")        
        self.claw_color = QColor("#D4D1B8")     
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(16)
        
    def _animate(self):
        self.phase += 0.04
        self.force_phase += 0.06
        self.float_y = math.sin(self.phase) * 3
        
        if not self.is_blinking:
            if random.random() < 0.005:
                self.is_blinking = True
        else:
            self.blink_phase -= 0.25 
            if self.blink_phase <= 0:
                self.blink_phase = 0
                self.is_blinking = False
        
        if not self.is_blinking and self.blink_phase < 1.0:
            self.blink_phase += 0.15 
            if self.blink_phase >= 1.0:
                self.blink_phase = 1.0
                
        if random.random() < 0.005:
            self._target_ear_twitch = random.uniform(-5, 5)
        self.ear_twitch += (self._target_ear_twitch - self.ear_twitch) * 0.1
        
        if random.random() < 0.005:
            self._target_head_tilt = random.uniform(-4, 4)
        self.head_tilt += (self._target_head_tilt - self.head_tilt) * 0.04
        
        self.update()

    def paintEvent(self, event):
        """Main render loop for Grogu.
        
        Uses a hierarchical coordinate system (translate/rotate/scale) to 
        position the various body parts relative to the center.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        p.translate(cx, cy)
        p.scale(0.8, 0.8)
        p.translate(0, 30)
        
        p.save()
        p.translate(0, self.float_y * 0.3)
        self._draw_robe_body(p)
        p.restore()
        
        self._draw_arms_and_hands(p)
        self._draw_force_ball(p)
        
        p.save()
        p.translate(0, self.float_y * 0.6)
        self._draw_collar(p)
        p.restore()
        
        p.save()
        p.translate(0, -50 + self.float_y)
        p.rotate(self.head_tilt)
        
        self._draw_ears(p)
        self._draw_head_silhouette(p)
        self._draw_eyes(p)
        self._draw_face_details(p)
        self._draw_peach_fuzz(p)
        
        p.restore()

    def _draw_robe_body(self, p):
        body_path = QPainterPath()
        body_path.moveTo(-80, -20)
        body_path.cubicTo(-130, 40, -150, 160, -140, 250)
        body_path.lineTo(140, 250)
        body_path.cubicTo(150, 160, 130, 40, 80, -20)
        body_path.closeSubpath()

        grad = QLinearGradient(-140, 0, 140, 0)
        grad.setColorAt(0.0, self.robe_shadow.darker(130))
        grad.setColorAt(0.2, self.robe_base)
        grad.setColorAt(0.8, self.robe_base)
        grad.setColorAt(1.0, self.robe_shadow.darker(150))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(body_path)
        
        seam_path = QPainterPath()
        seam_path.moveTo(-10, -20)
        seam_path.cubicTo(-5, 60, -15, 140, 0, 250)
        p.setPen(QPen(self.robe_shadow.darker(140), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(seam_path)

    def _draw_arms_and_hands(self, p):
        p.save()
        p.translate(110, 80)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(15, 10, 5, 255))
        p.drawEllipse(QRectF(-25, 10, 55, 30))
        p.setBrush(self.skin_shadow)
        p.drawEllipse(QRectF(-14, 20, 28, 24)) 
        p.setBrush(self.skin_base)
        for fx, fy, rot in [(-12, 36, 15), (0, 40, 0), (12, 36, -15)]:
            p.save()
            p.translate(fx, fy)
            p.rotate(rot)
            p.drawEllipse(QRectF(-7, -10, 14, 20))
            p.setBrush(self.claw_color)
            p.drawEllipse(QRectF(-2.5, 8, 5, 6))
            p.restore()
        cuff_path = QPainterPath()
        cuff_path.moveTo(-40, -20)
        cuff_path.cubicTo(45, -35, 55, 15, 35, 35)
        cuff_path.cubicTo(0, 45, -45, 25, -40, -20)
        grad = QLinearGradient(-40, 0, 40, 0)
        grad.setColorAt(0, self.robe_shadow)
        grad.setColorAt(0.5, self.robe_base)
        grad.setColorAt(1, self.robe_shadow.darker())
        p.setBrush(grad)
        p.drawPath(cuff_path)
        p.restore()
        
        p.save()
        p.translate(-110, 60 + self.float_y * 0.2)
        p.rotate(-30)
        p.setBrush(QColor(15, 10, 5, 255))
        p.drawEllipse(QRectF(-30, -5, 55, 30))
        p.setBrush(self.skin_base)
        p.drawEllipse(QRectF(-18, -14, 32, 28)) 
        for fx, fy, rot in [(-14, -10, -45), (-4, -20, -15), (12, -14, 25)]:
            p.save()
            p.translate(fx, fy)
            p.rotate(rot)
            p.setBrush(self.skin_light)
            p.drawEllipse(QRectF(-6, -14, 12, 20))
            p.setBrush(self.claw_color)
            p.drawEllipse(QRectF(-2.5, -18, 5, 6))
            p.restore()
        cuff_path = QPainterPath()
        cuff_path.moveTo(-40, -5)
        cuff_path.cubicTo(40, -25, 50, 15, 40, 30)
        cuff_path.cubicTo(0, 40, -50, 20, -40, -5)
        p.setBrush(grad)
        p.drawPath(cuff_path)
        p.restore()

    def _draw_force_ball(self, p):
        ball_x = -160
        ball_y = -10 + math.sin(self.force_phase) * 15 + self.float_y * 0.2
        glow = QRadialGradient(ball_x, ball_y, 50)
        glow.setColorAt(0, QColor(160, 220, 255, 90))
        glow.setColorAt(1, QColor(160, 220, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(ball_x - 50, ball_y - 50, 100, 100))
        sphere_rect = QRectF(ball_x - 16, ball_y - 16, 32, 32)
        grad = QRadialGradient(ball_x - 7, ball_y - 7, 22)
        grad.setColorAt(0.0, QColor(255, 255, 255))
        grad.setColorAt(0.3, QColor(190, 200, 210))
        grad.setColorAt(0.7, QColor(90, 100, 110))
        grad.setColorAt(1.0, QColor(50, 55, 60))
        p.setBrush(grad)
        p.drawEllipse(sphere_rect)
        p.setBrush(QColor(255, 255, 255, 120))
        p.drawArc(QRectF(ball_x - 14, ball_y - 14, 28, 28), 45 * 16, 90 * 16)

    def _draw_collar(self, p):
        p.setPen(Qt.PenStyle.NoPen)
        collar_path = QPainterPath()
        collar_path.moveTo(-130, 0)
        collar_path.cubicTo(-70, -30, 70, -30, 130, 5) 
        collar_path.cubicTo(160, 50, 120, 80, 70, 85)
        collar_path.cubicTo(0, 95, -70, 85, -120, 60)
        collar_path.cubicTo(-150, 35, -130, 0, -130, 0)
        grad = QLinearGradient(-130, -30, 130, 85)
        grad.setColorAt(0.0, self.fleece.lighter(110))
        grad.setColorAt(0.5, self.fleece)
        grad.setColorAt(1.0, self.robe_shadow.darker(120))
        p.setBrush(grad)
        p.drawPath(collar_path)
        
        p.setPen(QPen(self.robe_shadow.darker(110), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        fold1 = QPainterPath()
        fold1.moveTo(-90, 25)
        fold1.cubicTo(-40, 45, 50, 45, 90, 35)
        p.drawPath(fold1)
        fold2 = QPainterPath()
        fold2.moveTo(-70, 55)
        fold2.cubicTo(-30, 70, 40, 70, 70, 60)
        p.drawPath(fold2)

    def _draw_ears(self, p):
        for side in [-1, 1]:
            p.save()
            p.scale(side, 1)
            
            p.translate(110, -50) 
            p.rotate((self.ear_twitch + 5) * side) 
            
            outer_path = QPainterPath()
            outer_path.moveTo(-30, -30) 
            outer_path.cubicTo(80, -60, 180, -40, 260, -15) 
            outer_path.cubicTo(270, 0, 250, 25, 200, 20) 
            outer_path.cubicTo(100, 10, 30, 35, -30, 40) 
            outer_path.closeSubpath()
            
            grad = QLinearGradient(-30, -30, 260, 0)
            grad.setColorAt(0.0, self.skin_base)
            grad.setColorAt(0.3, self.skin_light)
            grad.setColorAt(1.0, self.skin_shadow)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawPath(outer_path)
            
            inner_path = QPainterPath()
            inner_path.moveTo(-10, -15)
            inner_path.cubicTo(80, -35, 180, -20, 230, -5) 
            inner_path.cubicTo(235, 5, 210, 10, 130, 5) 
            inner_path.cubicTo(50, 0, -10, 10, -10, 10)
            inner_path.closeSubpath()
            
            inner_grad = QLinearGradient(-10, -15, 230, 5)
            inner_grad.setColorAt(0.0, self.ear_deep)        
            inner_grad.setColorAt(0.3, self.ear_inner.darker(110))
            inner_grad.setColorAt(0.8, self.ear_inner)       
            inner_grad.setColorAt(1.0, self.skin_light)  
            p.setBrush(inner_grad)
            p.drawPath(inner_path)
            p.restore()

    def _draw_head_silhouette(self, p):
        head_path = QPainterPath()
        head_path.moveTo(0, 60) 
        head_path.cubicTo(80, 60, 135, 30, 140, -10)  
        head_path.cubicTo(145, -45, 125, -60, 115, -70) 
        head_path.cubicTo(125, -110, 80, -140, 0, -140)  
        head_path.cubicTo(-80, -140, -125, -110, -115, -70) 
        head_path.cubicTo(-125, -60, -145, -45, -140, -10) 
        head_path.cubicTo(-135, 30, -80, 60, 0, 60) 
        
        grad = QRadialGradient(0, -40, 140)
        grad.setColorAt(0.0, self.skin_light)
        grad.setColorAt(0.6, self.skin_base)
        grad.setColorAt(0.9, self.skin_shadow)
        grad.setColorAt(1.0, self.skin_deep)
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawPath(head_path)

        brow = QRadialGradient(0, -80, 60)
        brow.setColorAt(0.0, QColor(255, 255, 255, 40))
        brow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(brow)
        p.drawEllipse(QRectF(-60, -110, 120, 60))

    def _draw_eyes(self, p):
        """
        Refined eye shape: Wide, bowl-shaped with a heavy top lid.
        Symmetrical geometry ensures consistency.
        """
        eye_w = 95  # Slightly wider
        eye_h = 80
        eye_x = 60  # Wider spacing
        eye_y = -70 
        
        for side in [-1, 1]:
            p.save()
            p.translate(eye_x * side, eye_y + eye_h/2)
            p.scale(side, 1) 
            
            # 1. Soft socket shadow - deeper and more organic
            p.setPen(Qt.PenStyle.NoPen)
            socket = QRadialGradient(0, 0, eye_w*0.7)
            socket.setColorAt(0.0, QColor(0, 0, 0, 160)) 
            socket.setColorAt(0.6, QColor(self.skin_deep.red(), self.skin_deep.green(), self.skin_deep.blue(), 40))
            socket.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(socket)
            p.drawEllipse(QRectF(-eye_w*0.9, -eye_h*0.8, eye_w*1.8, eye_h*1.6))
            
            # 2. Refined Grogu Eye Mask
            mask = QPainterPath()
            # Start at inner corner
            mask.moveTo(-eye_w*0.48, -eye_h*0.05)
            
            # Upper lid: Heavy, flatter top that curves down at the outer corner
            top_y = -eye_h * 0.45 * self.blink_phase
            mask.cubicTo(-eye_w*0.2, top_y - 8, eye_w*0.3, top_y + 10, eye_w*0.48, eye_h*0.15)
            
            # Lower lid: Very round bowl shape
            mask.cubicTo(eye_w*0.4, eye_h*0.55, -eye_w*0.4, eye_h*0.5, -eye_w*0.48, -eye_h*0.05)
            mask.closeSubpath()
            
            p.setClipPath(mask)
            
            # 3. Eyeball (Massive deep black)
            p.save()
            eye_rect = QRectF(-eye_w/2, -eye_h/2, eye_w, eye_h)
            eye_grad = QRadialGradient(0, 0, eye_w*0.5)
            eye_grad.setColorAt(0.0, QColor(5, 5, 5)) 
            eye_grad.setColorAt(0.8, QColor(15, 10, 5))
            eye_grad.setColorAt(0.95, self.eye_rim) 
            eye_grad.setColorAt(1.0, QColor(0, 0, 0))
            
            p.setBrush(eye_grad)
            p.drawEllipse(eye_rect) 
            p.restore()
            
            # 4. Refined Reflections (Soulful catchlights)
            p.save()
            p.scale(side, 1) 
            
            # Main sky reflection
            sky_glint = QLinearGradient(-eye_w*0.3, -eye_h*0.4, eye_w*0.3, 0)
            sky_glint.setColorAt(0.0, QColor(255, 255, 255, 160))
            sky_glint.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(sky_glint)
            p.drawChord(QRectF(-eye_w*0.4, -eye_h*0.45, eye_w*0.8, eye_h*0.6), 30 * 16, 120 * 16)
            
            # Two distinct catchlights for that "filmic" look
            p.setBrush(QColor(255, 255, 255, 255))
            p.drawEllipse(QRectF(-eye_w*0.2, -eye_h*0.3, 14, 14)) # Primary
            p.setBrush(QColor(255, 255, 255, 120))
            p.drawEllipse(QRectF(eye_w*0.1, -eye_h*0.15, 6, 6))  # Secondary
            
            ground_bounce = QRadialGradient(0, eye_h*0.4, eye_w*0.4)
            ground_bounce.setColorAt(0.0, QColor(150, 180, 150, 50))
            ground_bounce.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(ground_bounce)
            p.drawEllipse(QRectF(-eye_w*0.4, eye_h*0.1, eye_w*0.8, eye_h*0.4))
            p.restore()
            
            # 5. Eyelid Creases (Organic skin folds)
            p.setClipping(False) 
            
            # Upper crease - follows the heavy lid
            p.setPen(QPen(self.skin_deep.darker(115), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            crease = QPainterPath()
            crease.moveTo(-eye_w*0.5, -eye_h*0.05)
            crease.cubicTo(-eye_w*0.2, top_y - 18, eye_w*0.3, top_y + 5, eye_w*0.5 + 5, eye_h*0.2)
            p.drawPath(crease)
            
            # Lower bag - more pronounced for "baby" look
            p.setPen(QPen(self.skin_shadow, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            lower_lid = QPainterPath()
            lower_lid.moveTo(-eye_w*0.45, eye_h*0.25)
            lower_lid.cubicTo(-eye_w*0.1, eye_h*0.6, eye_w*0.3, eye_h*0.6, eye_w*0.45, eye_h*0.3)
            p.drawPath(lower_lid)
            
            p.restore()

    def _draw_face_details(self, p):
        """Proportions: Nose at baseline, mouth tucked. Added soft aging/expression lines."""
        p.setPen(Qt.PenStyle.NoPen)
        def draw_soft_crease(x, y, w, h, alpha=60):
            grad = QRadialGradient(x + w/2, y + h/2, w/2)
            grad.setColorAt(0.0, QColor(self.skin_deep.red(), self.skin_deep.green(), self.skin_deep.blue(), alpha)) 
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(grad)
            p.drawEllipse(QRectF(x, y, w, h))

        # Soft forehead wrinkles
        draw_soft_crease(-50, -100, 100, 20, 35)
        draw_soft_crease(-40, -85, 80, 15, 25)

        # --- Nose (at baseline of eyes) ---
        nose_y = 10
        p.setPen(Qt.PenStyle.NoPen)
        draw_soft_crease(-15, nose_y - 12, 30, 20, 50) 
        
        p.setPen(QPen(self.skin_deep.darker(160), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # Nose holes
        p.drawArc(QRectF(-9, nose_y + 2, 6, 4), 45 * 16, 90 * 16)
        p.drawArc(QRectF(3, nose_y + 2, 6, 4), 45 * 16, 90 * 16)
        
        # Tip highlight
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 50))
        p.drawEllipse(QRectF(-4, nose_y, 8, 5))

        # --- Mouth (tucked under nose) ---
        mouth_y = 32
        p.setPen(QPen(self.skin_deep.darker(140), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        mouth_path = QPainterPath()
        mouth_path.moveTo(-12, mouth_y)
        mouth_path.quadTo(0, mouth_y + 4, 12, mouth_y) 
        p.drawPath(mouth_path)
        
        # Lower lip highlight
        p.setPen(QPen(self.skin_light, 1.2))
        p.drawArc(QRectF(-6, mouth_y + 1, 12, 4), -30 * 16, -120 * 16) 
        
        # Chin shadow
        p.setPen(Qt.PenStyle.NoPen)
        draw_soft_crease(-15, mouth_y + 8, 30, 12, 60)

        # --- Cheeks ---
        for cx in [-55, 55]: 
            blush = QRadialGradient(cx, 15, 50)
            blush.setColorAt(0.0, QColor(160, 100, 100, 45)) 
            blush.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(blush)
            p.drawEllipse(QRectF(cx - 45, 15 - 35, 90, 70))

    def _draw_peach_fuzz(self, p):
        p.setPen(QPen(QColor(255, 255, 255, 70), 0.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        rand = random.Random(44)
        for _ in range(50):
            hx = rand.uniform(-50, 50)
            hy = -140 + (abs(hx) * 0.2) + rand.uniform(-4, 4)
            length = rand.uniform(5, 12)
            angle = math.radians(rand.uniform(230, 310))
            if hx < 0: angle = math.radians(rand.uniform(210, 260))
            if hx > 0: angle = math.radians(rand.uniform(280, 330))
            
            end_x = hx + math.cos(angle) * length
            end_y = hy + math.sin(angle) * length
            
            hair_path = QPainterPath()
            hair_path.moveTo(hx, hy)
            hair_path.quadTo(hx, hy - length*0.4, end_x, end_y)
            p.drawPath(hair_path)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("BioPro AI - Project Grogu")
    window.resize(700, 700)
    window.setStyleSheet("background-color: #050505;") 
    
    layout = QVBoxLayout(window)
    grogu = GroguAI()
    layout.addWidget(grogu, alignment=Qt.AlignmentFlag.AlignCenter)
    
    window.show()
    sys.exit(app.exec())