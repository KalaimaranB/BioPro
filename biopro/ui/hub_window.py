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
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget
from biopro.ui.theme import Colors

class ProgrammaticLoader(QWidget):
    """A procedural 3D rotating DNA double helix animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.angle = 0.0
        
        # Smooth 60 FPS animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)

    def _update_animation(self):
        self.angle += 0.03  # Rotation speed
        if self.angle >= math.pi * 2:
            self.angle = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cy = self.height() / 2
        cx = self.width() / 2
        
        num_bases = 14       # How many base pairs tall
        spacing = 9          # Vertical space between pairs
        amplitude = 35       # Width of the helix
        twist = 0.45         # How tightly the helix twists
        
        start_y = cy - (num_bases * spacing) / 2
        
        # 1. Calculate all coordinates and depths
        points = []
        for i in range(num_bases):
            y = start_y + i * spacing
            
            # Strand 1 (Phase)
            phase1 = self.angle + (i * twist)
            x1 = cx + math.sin(phase1) * amplitude
            z1 = math.cos(phase1)  # Depth: +1 is front, -1 is back
            
            # Strand 2 (Opposite Phase)
            phase2 = phase1 + math.pi
            x2 = cx + math.sin(phase2) * amplitude
            z2 = math.cos(phase2)
            
            points.append({'y': y, 'x1': x1, 'z1': z1, 'x2': x2, 'z2': z2})
            
        # 2. Draw base pair connections (Hydrogen bonds)
        # We make them slightly transparent so they sit in the "background"
        bond_pen = QPen(QColor(Colors.BORDER_FOCUS))
        bond_pen.setWidth(2)
        painter.setPen(bond_pen)
        for p in points:
            painter.drawLine(int(p['x1']), int(p['y']), int(p['x2']), int(p['y']))
            
        # 3. Draw the sugar-phosphate backbone dots
        painter.setPen(Qt.PenStyle.NoPen)
        for p in points:
            # Scale size based on depth (Z) to fake 3D perspective
            s1 = 5 + (p['z1'] * 2.5)
            s2 = 5 + (p['z2'] * 2.5)
            
            # Darken the dots that are rotating behind the helix
            c1 = QColor(Colors.ACCENT_PRIMARY) if p['z1'] > 0 else QColor(Colors.ACCENT_PRIMARY_HOVER)
            c2 = QColor(Colors.ACCENT_PRIMARY) if p['z2'] > 0 else QColor(Colors.ACCENT_PRIMARY_HOVER)
            if p['z1'] <= 0: c1.setAlpha(150)
            if p['z2'] <= 0: c2.setAlpha(150)
            
            painter.setBrush(c1)
            painter.drawEllipse(int(p['x1'] - s1/2), int(p['y'] - s1/2), int(s1), int(s1))
            
            painter.setBrush(c2)
            painter.drawEllipse(int(p['x2'] - s2/2), int(p['y'] - s2/2), int(s2), int(s2))

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
        
        lbl_title = QLabel("BioPro")
        lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;")
        
        lbl_badge = QLabel("BETA")
        lbl_badge.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; background: transparent; "
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; "
            f"padding: 2px 6px; font-size: 10px; font-weight: bold; margin-top: 15px;"
        )
        
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(lbl_badge)
        right_layout.addLayout(title_layout)

        # 3. Broadened Subtitles
        lbl_subtitle = QLabel("The Extensible Bio-Image Analysis Ecosystem")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(lbl_subtitle)
        
        lbl_desc = QLabel("Modular · Open-Source · Python-Powered")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 13px; margin-bottom: 20px;")
        right_layout.addWidget(lbl_desc)

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