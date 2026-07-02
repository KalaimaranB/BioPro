from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from biopro.core.models.tutorial_models import Course
from biopro.core.tutorial_manager import global_tutorial_manager


class AcademyCourseCard(QFrame):
    """A card representing a single course."""

    start_requested = pyqtSignal(str)
    resume_requested = pyqtSignal(str)
    restart_requested = pyqtSignal(str)

    def __init__(self, course: Course, is_locked: bool, progress: float):
        super().__init__()
        self.course = course
        self.is_locked = is_locked
        self.progress = progress
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            AcademyCourseCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
            AcademyCourseCard:hover {
                border-color: #58a6ff;
            }
        """)
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        title = QLabel(self.course.title)
        title.setStyleSheet("color: #c9d1d9; font-size: 16px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        status_lbl = QLabel()
        if self.is_locked:
            status_lbl.setText("🔒 Locked")
            status_lbl.setStyleSheet("color: #8b949e; font-weight: bold;")
        elif self.progress == 100.0:
            status_lbl.setText("✅ Completed")
            status_lbl.setStyleSheet("color: #39ff14; font-weight: bold;")
        elif self.progress > 0:
            status_lbl.setText("⏳ In Progress")
            status_lbl.setStyleSheet("color: #d29922; font-weight: bold;")
        else:
            status_lbl.setText("Not Started")
            status_lbl.setStyleSheet("color: #8b949e;")

        header.addWidget(status_lbl)
        layout.addLayout(header)

        # Details
        desc = QLabel(self.course.description)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        duration = QLabel(f"⏱ ~{self.course.estimated_minutes} min")
        duration.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(duration)

        # Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        self.pbar.setMaximum(100)
        self.pbar.setValue(int(self.progress))
        self.pbar.setStyleSheet("""
            QProgressBar { background-color: #010409; border-radius: 3px; }
            QProgressBar::chunk { background-color: #238636; border-radius: 3px; }
        """)
        layout.addWidget(self.pbar)

        # Buttons
        btn_layout = QHBoxLayout()
        if not self.is_locked:
            if self.progress == 0:
                btn_start = QPushButton("Start Course →")
                btn_start.setStyleSheet(
                    "background-color: #2ea043; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
                )
                btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_start.clicked.connect(lambda: self.start_requested.emit(self.course.id))
                btn_layout.addWidget(btn_start)
            else:
                btn_resume = QPushButton("Resume →")
                btn_resume.setStyleSheet(
                    "background-color: #1f6feb; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold;"
                )
                btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_resume.clicked.connect(lambda: self.resume_requested.emit(self.course.id))
                btn_layout.addWidget(btn_resume)

                btn_restart = QPushButton("Restart")
                btn_restart.setStyleSheet(
                    "background-color: transparent; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; padding: 6px 12px;"
                )
                btn_restart.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_restart.clicked.connect(lambda: self.restart_requested.emit(self.course.id))
                btn_layout.addWidget(btn_restart)
        else:
            reqs = QLabel("⚠ Requires: " + ", ".join(self.course.prerequisite_course_ids))
            reqs.setStyleSheet("color: #d29922; font-size: 12px; font-weight: bold;")
            btn_layout.addWidget(reqs)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class AcademyDashboard(QWidget):
    """The main hub for the BioPro Academy."""

    close_requested = pyqtSignal()
    start_course_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = global_tutorial_manager
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background-color: #0d1117;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("🎓 BioPro Academy")
        title.setStyleSheet("color: #c9d1d9; font-size: 28px; font-weight: bold;")
        title_box.addWidget(title)

        subtitle = QLabel("Learn by doing real science.")
        subtitle.setStyleSheet("color: #8b949e; font-size: 16px;")
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        btn_close = QPushButton("× Close")
        btn_close.setStyleSheet(
            "background: transparent; color: #8b949e; font-size: 18px; font-weight: bold; border: none;"
        )
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close_requested.emit)
        header.addWidget(btn_close)

        main_layout.addLayout(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(30)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        self._build_badges()
        self._build_courses()
        self.content_layout.addStretch()

    def _build_badges(self):
        lbl = QLabel("🏅 YOUR BADGES")
        lbl.setStyleSheet(
            "color: #8b949e; font-weight: bold; font-size: 13px; letter-spacing: 1px;"
        )
        self.content_layout.addWidget(lbl)

        badge_container = QWidget()
        badge_layout = QHBoxLayout(badge_container)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setSpacing(15)

        earned_ids = [b["id"] for b in self.manager.badges]

        # Collect all possible badges from registered courses
        for _module_id, courses in self.manager.courses_by_module.items():
            for course in courses:
                if not course.badge_reward:
                    continue

                is_earned = course.id in earned_ids

                b_widget = QFrame()
                b_widget.setFixedSize(100, 120)
                if is_earned:
                    b_widget.setStyleSheet(
                        "background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; border-bottom: 3px solid #d29922;"
                    )
                else:
                    b_widget.setStyleSheet(
                        "background-color: #010409; border: 1px dashed #30363d; border-radius: 8px;"
                    )

                bl = QVBoxLayout(b_widget)
                bl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                icon = QLabel(course.badge_icon if is_earned else "🔒")
                icon.setStyleSheet(
                    f"font-size: 32px; color: {'#c9d1d9' if is_earned else '#484f58'};"
                )
                icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                bl.addWidget(icon)

                name = QLabel(course.badge_reward if is_earned else "Locked")
                name.setWordWrap(True)
                name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                name.setStyleSheet(
                    f"color: {'#c9d1d9' if is_earned else '#484f58'}; font-size: 11px; font-weight: bold;"
                )
                bl.addWidget(name)

                badge_layout.addWidget(b_widget)

        badge_layout.addStretch()
        self.content_layout.addWidget(badge_container)

    def _build_courses(self):
        for module_id, courses in self.manager.courses_by_module.items():
            mod_lbl = QLabel(f"{module_id.replace('_', ' ').upper()} MODULE")
            mod_lbl.setStyleSheet(
                "color: #8b949e; font-weight: bold; font-size: 13px; letter-spacing: 1px; margin-top: 10px;"
            )
            self.content_layout.addWidget(mod_lbl)

            grid = QGridLayout()
            grid.setSpacing(15)

            for i, course in enumerate(courses):
                is_locked = False
                for prereq in course.prerequisite_course_ids:
                    if prereq not in self.manager.completed_courses:
                        is_locked = True
                        break

                progress = self.manager.get_progress(course.id)
                card = AcademyCourseCard(course, is_locked, progress)
                card.start_requested.connect(self._handle_course_action)
                card.resume_requested.connect(self._handle_course_action)
                card.restart_requested.connect(self._handle_course_action)
                grid.addWidget(card, i // 2, i % 2)

            self.content_layout.addLayout(grid)

    def _handle_course_action(self, course_id: str):
        self.manager.start_course(course_id)
        self.start_course_requested.emit(course_id)
