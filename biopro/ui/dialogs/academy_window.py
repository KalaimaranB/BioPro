import math
import random

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors, Fonts


class Particle:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.radius = random.uniform(1.5, 3.5)

    def update(self, w, h):
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > w:
            self.vx *= -1
        if self.y < 0 or self.y > h:
            self.vy *= -1


class AcademyWindow(QDialog):
    """
    The centralized Course Hub UI for the BioPro Academy.
    Displays all available courses for a given module and tracks progress.
    """

    def __init__(self, tutorial_manager, module_id: str, parent=None):
        super().__init__(parent)
        self.tutorial_manager = tutorial_manager
        self.module_id = module_id

        self.setWindowTitle(f"BioPro Academy - {module_id.capitalize()} Courses")
        self.setMinimumSize(800, 500)

        # No stylesheet background because we use custom paintEvent for particles
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Setup Particle Engine
        self.particles = [Particle(800, 500) for _ in range(40)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_particles)
        self.timer.start(30)  # ~33 fps

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 20)
        self.layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.header = QLabel("Available Courses")
        self.header.setFont(Fonts.H1)

        self.header_desc = QLabel("Master the techniques of bio analysis.")
        self.header_desc.setFont(Fonts.BODY)

        header_vbox = QVBoxLayout()
        header_vbox.addWidget(self.header)
        header_vbox.addWidget(self.header_desc)

        header_layout.addLayout(header_vbox)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Scroll Area for Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(10, 10, 10, 10)
        self.cards_layout.setSpacing(20)

        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        # Footer
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Close")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFont(Fonts.BODY)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        self.layout.addLayout(btn_layout)

        self._apply_styles()

        from biopro.ui.theme import theme_manager

        theme_manager.theme_changed.connect(self._apply_styles)

    def _apply_styles(self):
        self.header.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY};")
        self.header_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 24px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.BORDER_FOCUS};
            }}
        """)
        self._populate_courses()

    def _animate_particles(self):
        w, h = self.width(), self.height()
        for p in self.particles:
            p.update(w, h)
        self.update()

    def paintEvent(self, event):
        """Draw deep background and techy biology particles."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor(Colors.BG_DARKEST))

        # Draw connections (tech/biology node network)
        max_dist = 120
        pen = QPen(QColor(Colors.DNA_PRIMARY))

        for i, p1 in enumerate(self.particles):
            for p2 in self.particles[i + 1 :]:
                dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if dist < max_dist:
                    opacity = 1.0 - (dist / max_dist)
                    c = QColor(Colors.DNA_PRIMARY)
                    c.setAlphaF(opacity * 0.4)
                    pen.setColor(c)
                    pen.setWidthF(1.5)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

        # Draw particles
        painter.setPen(Qt.PenStyle.NoPen)
        for i, p in enumerate(self.particles):
            c = QColor(Colors.DNA_PRIMARY) if i % 2 == 0 else QColor(Colors.DNA_SECONDARY)
            c.setAlpha(150)
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)

    def _populate_courses(self):
        # Clear existing
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        courses = self.tutorial_manager.get_courses_for_module(self.module_id)

        if not courses:
            lbl = QLabel("No courses implemented yet. Check back soon!")
            lbl.setFont(Fonts.H2)
            lbl.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(lbl)
            return

        for course in courses:
            card = self._create_course_card(course)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _create_course_card(self, course) -> QWidget:
        def hex_to_rgba(hex_color: str, alpha: float) -> str:
            h = hex_color.lstrip("#")
            if len(h) == 6:
                return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha})"
            return hex_color

        card = QFrame()
        card.setObjectName("CourseCard")
        # Glassmorphism styling with border radius
        bg_dark_rgba = hex_to_rgba(Colors.BG_DARK, 0.85)
        bg_medium_rgba = hex_to_rgba(Colors.BG_MEDIUM, 0.95)

        card.setStyleSheet(f"""
            QFrame#CourseCard {{
                background-color: {bg_dark_rgba};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
            QFrame#CourseCard:hover {{
                border: 1px solid {Colors.BORDER_FOCUS};
                background-color: {bg_medium_rgba};
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Left Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        title = QLabel(course.title)
        title.setFont(Fonts.H2)
        title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; background: transparent;")
        info_layout.addWidget(title)

        if hasattr(course, "description") and course.description:
            desc = QLabel(course.description)
            desc.setFont(Fonts.BODY)
            desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; background: transparent;")
            desc.setWordWrap(True)
            info_layout.addWidget(desc)

        # Status / Badges
        progress = self.tutorial_manager.get_progress(course.id)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)

        # Pill status
        status_pill = QLabel()
        status_pill.setFont(Fonts.CAPTION)
        if progress >= 100.0:
            status_pill.setText(" COMPLETED ")
            success_rgba = hex_to_rgba(Colors.ACCENT_SUCCESS, 0.2)
            status_pill.setStyleSheet(f"""
                background-color: {success_rgba};
                color: {Colors.ACCENT_SUCCESS};
                border: 1px solid {Colors.ACCENT_SUCCESS};
                border-radius: 10px;
                padding: 4px 8px;
                font-weight: bold;
            """)
        else:
            status_pill.setText(" IN PROGRESS " if progress > 0 else " NOT STARTED ")
            secondary_rgba = hex_to_rgba(Colors.FG_SECONDARY, 0.1)
            status_pill.setStyleSheet(f"""
                background-color: {secondary_rgba};
                color: {Colors.FG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                padding: 4px 8px;
                font-weight: bold;
            """)
        status_layout.addWidget(status_pill)

        if progress >= 100.0 and getattr(course, "badge_reward", None):
            badge = QLabel(f" AWARD: {course.badge_reward} ")
            badge.setFont(Fonts.CAPTION)
            warning_rgba = hex_to_rgba(Colors.ACCENT_WARNING, 0.15)
            badge.setStyleSheet(f"""
                background-color: {warning_rgba};
                color: {Colors.ACCENT_WARNING};
                border: 1px solid {Colors.ACCENT_WARNING};
                border-radius: 10px;
                padding: 4px 8px;
                font-weight: bold;
            """)
            status_layout.addWidget(badge)

        status_layout.addStretch()
        info_layout.addLayout(status_layout)

        layout.addLayout(info_layout, stretch=1)

        # Action Buttons (Start / Reset)
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)
        action_layout.addStretch()

        # Start/Review Button
        action_btn = QPushButton("Start Course" if progress < 100.0 else "Review Course")
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        action_btn.setFont(Fonts.BODY)

        if progress < 100.0:
            success_hover_rgba = hex_to_rgba(Colors.ACCENT_SUCCESS, 0.8)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.ACCENT_SUCCESS};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {success_hover_rgba}; }}
            """)
        else:
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.BG_MEDIUM};
                    color: {Colors.FG_PRIMARY};
                    border: 1px solid {Colors.BORDER_FOCUS};
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: {Colors.BORDER_FOCUS}; color: #ffffff; }}
            """)

        action_btn.clicked.connect(lambda _, cid=course.id: self._start_course(cid))
        action_layout.addWidget(action_btn)

        # Reset Progress Button (Only show if there is progress)
        if progress >= 100.0:
            reset_btn = QPushButton("Reset Progress")
            reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reset_btn.setFont(Fonts.CAPTION)
            danger_rgba = hex_to_rgba(Colors.ACCENT_DANGER, 0.1)
            reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.ACCENT_DANGER};
                    border: 1px solid {Colors.ACCENT_DANGER};
                    border-radius: 4px;
                    padding: 4px 10px;
                }}
                QPushButton:hover {{
                    background-color: {danger_rgba};
                }}
            """)
            reset_btn.clicked.connect(lambda _, cid=course.id: self._reset_course(cid))
            action_layout.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignRight)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        return card

    def _start_course(self, course_id: str):
        self.tutorial_manager.start_course(course_id)
        self.accept()

    def _reset_course(self, course_id: str):
        if hasattr(self.tutorial_manager, "reset_course"):
            self.tutorial_manager.reset_course(course_id)
            self._populate_courses()  # Refresh UI
