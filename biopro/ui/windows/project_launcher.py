"""BioPro Hub - Project selection and creation dashboard."""

import logging
from pathlib import Path
from biopro.ui.windows.workspace_window import WorkspaceWindow
from biopro.core.config import AppConfig
from biopro.core.module_manager import ModuleManager
from PyQt6.QtWidgets import QPushButton
from biopro.ui.theme import Colors, Fonts
import random
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient
from PyQt6.QtGui import QAction, QFont
from biopro.ui.theme import Colors, Fonts, theme_manager


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
from biopro.sdk.ui import PrimaryButton, SecondaryButton

logger = logging.getLogger(__name__)

class ProjectLauncherWindow(QMainWindow):
    """The main entry hub for creating and opening BioPro projects."""

    # We now REQUIRE the dependencies to be passed in!
    def __init__(self, module_manager, updater, store_callback, hub_callback):
        super().__init__()
        
        # Save the references
        self.module_manager = module_manager
        self.updater = updater
        self.open_store_callback = store_callback
        
        # ADD THIS LINE to save the hub callback so we can pass it to WorkspaceWindow later
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

        self._setup_menu_bar()
        self._setup_ui()
        self._apply_theme_styles()

        # Listen for global theme changes
        theme_manager.theme_changed.connect(self._on_theme_changed)
        
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
        self.left_panel = QWidget()
        self.left_panel.setStyleSheet(f"background-color: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};")
        self.left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        self.lbl_recent = QLabel("Recent Projects")
        self.lbl_recent.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold; border: none;")
        left_layout.addWidget(self.lbl_recent)

        

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
        
        main_layout.addWidget(self.left_panel)

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
        
        self.lbl_title = QLabel("BioPro")
        self.lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;")
        
        self.lbl_badge = QLabel("BETA")
        self.lbl_badge.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; background: transparent; "
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; "
            f"padding: 2px 6px; font-size: 10px; font-weight: bold; margin-top: 15px;"
        )
        
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_badge)
        right_layout.addLayout(title_layout)

        # 3. Broadened Subtitles
        self.lbl_subtitle = QLabel("The Extensible Bio-Image Analysis Ecosystem")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self.lbl_subtitle)
        
        self.lbl_desc = QLabel("Modular · Open-Source · Python-Powered")
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
        # Pass self.module_manager instead of the undefined variable
        self.workspace = WorkspaceWindow(
            project_manager,
            self.module_manager,
            self.updater,
            self.open_store_callback,  # Fixed name
            self.return_to_hub_callback # Fixed name
        )
        self.workspace.show()
        self.close()

    def _open_store(self):
        """Tells the main Controller that the user wants to open the store."""
        self.open_store_callback(self)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        scale = max(1.0, min(self.width() / 800.0, 1.8))
        
        try:
            # Increase DNA size but keep it centered
            # We increase the 'box' so the fade has room to reach 0 alpha
            anim_sz = int(320 * scale) # Increased from 180
            self.animation_widget.setFixedSize(anim_sz, anim_sz)
            
            # Update Title & Subtitle Colors (This forces them to re-read the theme)
            self.lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: {int(42 * scale)}px; font-weight: 900;")
            self.lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: {int(16 * scale)}px; font-weight: bold;")
            self.lbl_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: {int(13 * scale)}px;")
            
            # Update the Window Background itself
            self.setStyleSheet(f"QMainWindow {{ background-color: {Colors.BG_DARKEST}; }}")
        except AttributeError:
            pass
    
    def refresh_ui(self):
        """The Hub doesn't display module buttons natively, so we pass."""
        pass

    def _setup_menu_bar(self):
        """Adds the Theme menu to the Hub so you can switch before entering a project."""
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("&Theme")
        
        action_default = QAction("BioPro Default", self)
        action_default.triggered.connect(lambda: self._switch_theme("default.json"))
        theme_menu.addAction(action_default)
        
        action_sw = QAction("Star Wars (Dark Side)", self)
        action_sw.triggered.connect(lambda: self._switch_theme("star_wars.json"))
        theme_menu.addAction(action_sw)

    def _switch_theme(self, filename: str):
        from pathlib import Path
        # Assuming themes is 2 levels up from biopro/ui/
        theme_path = Path(__file__).parent.parent.parent / "themes" / filename
        theme_manager.load_theme(theme_path)

    def _on_theme_changed(self):
        """Refreshes the Hub visuals when the theme changes."""
        self._apply_theme_styles()
        if hasattr(self, 'left_panel'):
            self.left_panel.setStyleSheet(
                f"background-color: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};"
            )
        if hasattr(self, 'lbl_recent'):
            self.lbl_recent.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold; border: none;"
            )
        if hasattr(self, 'lbl_title'):
            self.lbl_title.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;")
        if hasattr(self, 'lbl_badge'):
            self.lbl_badge.setStyleSheet(
                f"color: {Colors.ACCENT_PRIMARY}; background: transparent; "
                f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; "
                f"padding: 2px 6px; font-size: 10px; font-weight: bold; margin-top: 15px;"
            )
        if hasattr(self, 'lbl_subtitle'):
            self.lbl_subtitle.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;")
        if hasattr(self, 'lbl_desc'):
            self.lbl_desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 13px; margin-bottom: 20px;")
        # Trigger a resize event to force dynamic elements to redraw
        self.resizeEvent(None)

    def _apply_theme_styles(self):
        """Sets the styleSheet using the LATEST color values."""
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
        """)
        # Update the left panel specifically if it's already created
        if hasattr(self, 'list_recent'):
            self.list_recent.setStyleSheet(
                f"QListWidget {{ border: none; background: transparent; color: {Colors.FG_SECONDARY}; }}"
                f"QListWidget::item {{ padding: 10px; border-radius: 5px; }}"
                f"QListWidget::item:hover {{ background: {Colors.BG_MEDIUM}; }}"
                f"QListWidget::item:selected {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; font-weight: bold; }}"
            )

from PyQt6.QtCore import QThread, pyqtSignal

class ModuleLoaderWorker(QThread):
    """Dynamically loads a module and injects workflow data without freezing the Hub."""
    # Emits the fully instantiated panel widget back to the main thread
    finished = pyqtSignal(object) 
    error = pyqtSignal(str)

    def __init__(self, module_id, workflow_data=None):
        super().__init__()
        self.module_id = module_id
        self.workflow_data = workflow_data

    def run(self):
        try:
            # 1. Dynamically import the module (this is what usually causes the lag)
            import importlib
            module_path = f"biopro.plugins.{self.module_id}.ui.main_panel"
            mod = importlib.import_module(module_path)
            
            # Note: You will need to make sure your plugins have a standard class name
            # or a factory function to grab the main widget.
            # Assuming your modules have a standard 'get_panel()' function or similar:
            panel_class = getattr(mod, "CytoMetricsPanel") # Adjust to your dynamic loading logic
            
            # We can't actually instantiate QWidgets in a background thread without 
            # making PyQt angry, so we just import the heavy libraries and 
            # pass the Class reference back to the main thread to be built instantly.
            
            self.finished.emit((panel_class, self.workflow_data))
            
        except Exception as e:
            self.error.emit(str(e))