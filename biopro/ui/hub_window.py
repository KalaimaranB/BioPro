"""BioPro Hub - Project selection and creation dashboard."""

import logging
from pathlib import Path
from biopro.ui.main_window import MainWindow
from biopro.core.config import AppConfig
from biopro.core.module_manager import ModuleManager
from PyQt6.QtWidgets import QPushButton
from biopro.ui.theme import Colors, Fonts


from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie, QIcon, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from biopro.core.project_manager import ProjectManager, ProjectLockedError
from biopro.ui.theme import Colors

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

logger = logging.getLogger(__name__)

class HubWindow(QMainWindow):
    """The main entry hub for creating and opening BioPro projects."""

    def __init__(self):
        super().__init__()
        self.module_manager = ModuleManager()
        self.setWindowTitle("BioPro Hub")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"background-color: {Colors.BG_DARKEST};")
        
        self._setup_ui()
        self._load_recent_projects()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left Panel: Recent Projects ───────────────────────────────────
        left_panel = QWidget()
        left_panel.setStyleSheet(f"background-color: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};")
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        lbl_recent = QLabel("Recent Projects")
        lbl_recent.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        left_layout.addWidget(lbl_recent)

        

        self.list_recent = QListWidget()
        self.list_recent.setStyleSheet(
            f"QListWidget {{ border: none; background: transparent; color: {Colors.FG_SECONDARY}; }}"
            f"QListWidget::item {{ padding: 10px; border-radius: 5px; }}"
            f"QListWidget::item:hover {{ background: {Colors.BG_MEDIUM}; }}"
            f"QListWidget::item:selected {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; font-weight: bold; }}"
        )
        self.list_recent.itemDoubleClicked.connect(self._on_recent_double_clicked)
        left_layout.addWidget(self.list_recent)

        self.btn_store = QPushButton("☁️ Plugin Store & Updates")
        self.btn_store.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: 1px solid {Colors.ACCENT_PRIMARY};"
            f"  border-radius: 5px; padding: 10px;"
            f"  color: {Colors.ACCENT_PRIMARY}; font-size: {Fonts.SIZE_NORMAL}px; font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f"}}"
        )
        self.btn_store.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_store.clicked.connect(self._open_store)
        left_layout.addWidget(self.btn_store)
        
        main_layout.addWidget(left_panel)

        # ── Right Panel: Branding & Actions ───────────────────────────────
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.setSpacing(30)

        # 1. DNA Animation
        self.animation_widget = ProgrammaticLoader()
        right_layout.addWidget(self.animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 2. Title & Badge
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_title = QLabel("BioPro") # ADDED self.
        self.lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;")
        
        self.lbl_badge = QLabel("BETA") # ADDED self.
        self.lbl_badge.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; background: transparent; "
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; "
            f"padding: 2px 6px; font-size: 10px; font-weight: bold; margin-top: 15px;"
        )
        
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_badge)
        right_layout.addLayout(title_layout)

        # 3. Broadened Subtitles
        self.lbl_subtitle = QLabel("The Extensible Bio-Image Analysis Ecosystem") # ADDED self.
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_subtitle)
        
        self.lbl_desc = QLabel("Modular · Open-Source · Python-Powered") # ADDED self.
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 13px; margin-bottom: 20px;")
        right_layout.addWidget(self.lbl_desc)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_new = QPushButton("✨ Create New Project")
        self.btn_new.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f" border: none; border-radius: 6px; padding: 12px 24px; font-size: 13px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
        )
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self._on_new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_open = QPushButton("📁 Open Project...")
        self.btn_open.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};"
            f" border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: 12px 24px; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {Colors.BG_LIGHT}; }}"
        )
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._on_open_project)
        btn_layout.addWidget(self.btn_open)

        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel)

    # ── Logic ─────────────────────────────────────────────────────────

    def _load_recent_projects(self):
        self.list_recent.clear()
        
        config = AppConfig()
        recent_paths = config.get_recent_projects()
        
        if not recent_paths:
            item = QListWidgetItem("No recent projects")
            item.setFlags(Qt.ItemFlag.NoItemFlags) # Make it unclickable
            self.list_recent.addItem(item)
            return

        for path_str in recent_paths:
            path = Path(path_str)
            if path.exists():
                # Store the absolute path secretly in the UserRole data
                item = QListWidgetItem(f"📄 {path.name}")
                item.setData(Qt.ItemDataRole.UserRole, path_str)
                self.list_recent.addItem(item)

    def _on_new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Enter Project Name:")
        if not ok or not name.strip():
            return
            
        dir_path = QFileDialog.getExistingDirectory(self, "Select Empty Folder for Project Workspace")
        if not dir_path:
            return

        project_dir = Path(dir_path) / name.strip()
        
        try:
            pm = ProjectManager(project_dir)
            pm.create_new(name.strip())
            self._launch_workspace(pm)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create project:\n{str(e)}")

    def _on_open_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select BioPro Project Folder")
        if not dir_path:
            return
            
        self._attempt_open(Path(dir_path))

    def _on_recent_double_clicked(self, item: QListWidgetItem):
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if path_str:
            self._attempt_open(Path(path_str))

    def _attempt_open(self, project_dir: Path):
        try:
            pm = ProjectManager(project_dir)
            pm.open_project()
            self._launch_workspace(pm)
        except ProjectLockedError as e:
            QMessageBox.warning(self, "Project in Use", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project:\n{str(e)}")

    def _launch_workspace(self, project_manager: ProjectManager):
        """Transition from the Hub to the actual Analysis Workspace."""
        # 1. Save to global recents list
        config = AppConfig()
        config.add_recent_project(project_manager.project_dir)

        # 2. Transition the UI
        from biopro.ui.main_window import MainWindow
        # Pass self.module_manager instead of the undefined variable
        self.workspace = MainWindow(project_manager, self.module_manager) 
        self.workspace.show()
        self.close()

    def _open_store(self):
        """Launches the app-level plugin store."""
        # Local import to prevent circular dependencies at boot
        from biopro.ui.store_dialog import StoreDialog
        dialog = StoreDialog(self.module_manager, self)
        dialog.exec()

    def resizeEvent(self, event):
        """Dynamically scale the UI when the window changes size."""
        super().resizeEvent(event)
        
        # Calculate a scale multiplier based on the default width of 800px.
        # We cap it at 1.8x so it doesn't get ridiculously huge on 4K monitors.
        scale = max(1.0, min(self.width() / 800.0, 1.8))
        
        try:
            # Scale the DNA Widget
            anim_sz = int(180 * scale)
            self.animation_widget.setFixedSize(anim_sz, anim_sz)
            
            # Scale the Text
            self.lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: {int(42 * scale)}px; font-weight: 900; letter-spacing: 1px;")
            self.lbl_badge.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; background: transparent; border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; padding: 2px 6px; font-size: {int(10 * scale)}px; font-weight: bold; margin-top: {int(15 * scale)}px;")
            self.lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: {int(16 * scale)}px; font-weight: bold;")
            self.lbl_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: {int(13 * scale)}px; margin-bottom: 20px;")
            
            # Scale the Action Buttons
            btn_sz = int(13 * scale)
            pad_v = int(12 * scale)
            pad_h = int(24 * scale)
            
            self.btn_new.setStyleSheet(
                f"QPushButton {{ background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
                f" border: none; border-radius: 6px; padding: {pad_v}px {pad_h}px; font-size: {btn_sz}px; font-weight: bold; }}"
                f"QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}"
            )
            self.btn_open.setStyleSheet(
                f"QPushButton {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};"
                f" border: 1px solid {Colors.BORDER}; border-radius: 6px; padding: {pad_v}px {pad_h}px; font-size: {btn_sz}px; }}"
                f"QPushButton:hover {{ background-color: {Colors.BG_LIGHT}; }}"
            )
        except AttributeError:
            # Fails silently on the very first boot before the widgets are fully constructed
            pass