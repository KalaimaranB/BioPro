"""BioPro Hub - Project selection and creation dashboard."""

import logging
from pathlib import Path
from biopro.ui.main_window import MainWindow
from biopro.core.config import AppConfig
from biopro.core.module_manager import ModuleManager
from PyQt6.QtWidgets import QPushButton
from biopro.ui.theme import Colors, Fonts
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient


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
from biopro.ui.widgets.dna_loader import ProgrammaticLoader
from biopro.shared.ui.ui_components import PrimaryButton, SecondaryButton

logger = logging.getLogger(__name__)

class HubWindow(QMainWindow):
    """The main entry hub for creating and opening BioPro projects."""

    # We now REQUIRE the dependencies to be passed in!
    def __init__(self, module_manager, updater, store_callback, hub_callback):
        super().__init__()
        
        # Save the references
        self.module_manager = module_manager
        self.updater = updater
        self.open_store_callback = store_callback
        
        # ADD THIS LINE to save the hub callback so we can pass it to MainWindow later
        self.return_to_hub_callback = hub_callback
        self.setWindowTitle("BioPro Hub")
        self.setMinimumSize(800, 500)
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {Colors.BG_DARKEST}; }}
            QWidget {{ color: {Colors.FG_PRIMARY}; }}
            QLineEdit {{ 
                background-color: {Colors.BG_MEDIUM}; 
                border: 1px solid {Colors.BORDER}; 
                padding: 5px; 
                border-radius: 4px; 
            }}
            QLabel {{ background: transparent; }}
            QPushButton {{ 
                background-color: {Colors.BG_MEDIUM}; 
                border: 1px solid {Colors.BORDER};
                padding: 8px;
            }}
        """)
        
        self._setup_ui()
        self._load_recent_projects()
        # Initialize the Logic Engine for the Core App and Store
        # (Make sure to import NetworkUpdater at the top of your file!)
        from biopro.core.network_updater import NetworkUpdater 
        self.updater = NetworkUpdater()
        
        # Trigger the Core Update Check 0.5 seconds AFTER the Hub loads
        QTimer.singleShot(500, self.perform_startup_check)

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

        self.btn_store = SecondaryButton("☁️ Plugin Store & Updates")
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

        self.btn_new = PrimaryButton("✨ Create New Project")
        self.btn_new.clicked.connect(self._on_new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_open = SecondaryButton("📁 Open Project...")
        self.btn_open.clicked.connect(self._on_open_project)
        btn_layout.addWidget(self.btn_open)

        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel)

    # ── Logic ─────────────────────────────────────────────────────────
    def perform_startup_check(self):
        """Silently checks GitHub for Core App updates."""
        import webbrowser
        has_update, core_info = self.updater.check_for_core_updates()
        
        if has_update:
            msg = QMessageBox(self)
            msg.setWindowTitle("Update Available")
            msg.setText(f"A new version of BioPro (v{core_info.get('version', 'Unknown')}) is available!")
            msg.setInformativeText(core_info.get("release_notes", "Please update to the latest version."))
            
            # Add a custom button to take them to GitHub
            download_btn = msg.addButton("Download Now", QMessageBox.ButtonRole.AcceptRole)
            msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
            
            msg.exec()
            
            if msg.clickedButton() == download_btn:
                webbrowser.open(core_info.get('download_url', 'https://github.com/KalaimaranB/BioPro/releases'))

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

        selected_path = Path(dir_path)
        
        # Prevent "MyProject/MyProject" inception
        if selected_path.name == name.strip():
            project_dir = selected_path
        else:
            project_dir = selected_path / name.strip()
        
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
        self.workspace = MainWindow(
            project_manager, 
            self.module_manager, 
            self.updater,              
            self.open_store_callback,  
            self.return_to_hub_callback
        )
        self.workspace.show()
        self.close()

    def _open_store(self):
        """Tells the main Controller that the user wants to open the store."""
        self.open_store_callback(self)
        

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
            
            # We completely removed the button scaling here!
            # The UI components now manage themselves.
            
        except AttributeError:
            pass

    def refresh_ui(self):
        """The Hub doesn't display module buttons natively, so we pass."""
        pass