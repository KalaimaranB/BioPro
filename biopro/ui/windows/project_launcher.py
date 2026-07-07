"""BioPro Hub - Project selection and creation dashboard."""

import logging
from pathlib import Path

from biopro_sdk.plugin import PrimaryButton, SecondaryButton
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from biopro.core.config import AppConfig
from biopro.core.event_bus import get_event_bus
from biopro.core.project_manager import ProjectLockedError, ProjectManager
from biopro.core.update_checker import UpdateChecker
from biopro.ui.components.ai_panel import AIChatWindow
from biopro.ui.components.update_banner import UpdateBannerWidget
from biopro.ui.theme import Colors, theme_manager
from biopro.ui.widgets.dna_loader import ProgrammaticLoader
from biopro.ui.windows.workspace_window import WorkspaceWindow

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

        # Restore window geometry from preferences
        from PyQt6.QtCore import QByteArray

        from biopro.core.preferences import core_preferences

        saved_geom = core_preferences.get("hub_window_geometry")
        if saved_geom:
            self.restoreGeometry(QByteArray.fromHex(saved_geom.encode("ascii")))

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

        # Initialize the Logic Engine for the Core App and Store
        from biopro.core.network_updater import NetworkUpdater

        self.updater = NetworkUpdater()

        # Build update checker (injected deps — SRP + DIP)
        _config = AppConfig()
        self._update_checker = UpdateChecker(self.updater, _config, get_event_bus())

        self._setup_menu_bar()
        self._setup_ui()
        self._apply_theme_styles()

        # Listen for global theme changes
        theme_manager.theme_changed.connect(self._on_theme_changed)

        self._load_recent_projects()

        self._ai_window = None

        # Trigger background update check 0.5s after Hub loads (non-blocking)
        QTimer.singleShot(500, self._start_update_check_worker)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Outer vertical layout: banner on top, main panels below
        outer_layout = QVBoxLayout(central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Update banner — hidden by default, shown via event bus
        self.update_banner = UpdateBannerWidget(update_checker=self._update_checker, parent=self)
        outer_layout.addWidget(self.update_banner)

        # Main horizontal panel container
        panels_widget = QWidget()
        main_layout = QHBoxLayout(panels_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        outer_layout.addWidget(panels_widget, stretch=1)

        # ── Left Panel: Recent Projects ───────────────────────────────────
        self.left_panel = QWidget()
        self.left_panel.setStyleSheet(
            f"background-color: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};"
        )
        self.left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)

        self.lbl_recent = QLabel("Recent Projects")
        self.lbl_recent.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold; border: none;"
        )
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

        self.btn_store = SecondaryButton("☁️ Marketplace")
        self.btn_store.clicked.connect(self._open_store)
        left_layout.addWidget(self.btn_store)

        self.btn_ai = SecondaryButton("🧠 Gemma AI Assistant")
        self.btn_ai.clicked.connect(self._open_ai_chat)
        left_layout.addWidget(self.btn_ai)

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
        self.lbl_title.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;"
        )

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
        self.lbl_subtitle = QLabel("The Extensible BioPro Analysis Platform")
        self.lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        right_layout.addWidget(self.lbl_subtitle)

        self.lbl_desc = QLabel("Modular · Open-Source · Python-Powered")
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setStyleSheet(
            f"color: {Colors.FG_SECONDARY}; font-size: 13px; margin-bottom: 20px;"
        )
        right_layout.addWidget(self.lbl_desc)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_new = PrimaryButton("✨ Create New Project")
        self.btn_new.clicked.connect(self._on_new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_academy = SecondaryButton("🎓 Start Academy Course")
        self.btn_academy.setMinimumWidth(220)
        self.btn_academy.clicked.connect(self._on_academy_project)
        btn_layout.addWidget(self.btn_academy)

        self.btn_open = SecondaryButton("📁 Open Project...")
        self.btn_open.clicked.connect(self._on_open_project)
        btn_layout.addWidget(self.btn_open)

        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel)

    # ── Logic ─────────────────────────────────────────────────────────
    def _start_update_check_worker(self) -> None:
        """Launches a background thread to check for updates without blocking the UI."""
        self._update_worker = _UpdateCheckWorker(self._update_checker)
        self._update_worker.start()

    def _load_recent_projects(self):
        self.list_recent.clear()

        config = AppConfig()
        recent_paths = config.get_recent_projects()

        if not recent_paths:
            item = QListWidgetItem("No recent projects")
            item.setFlags(Qt.ItemFlag.NoItemFlags)  # Make it unclickable
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

        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Empty Folder for Project Workspace"
        )
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

    def _on_academy_project(self):
        name, ok = QInputDialog.getText(self, "Academy Project", "Enter Academy Project Name:")
        if not ok or not name.strip():
            return

        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Empty Folder for Academy Workspace"
        )
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
            pm.create_new(name.strip(), is_academy=True)
            self._launch_workspace(pm)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create academy project:\n{str(e)}")

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
            self.return_to_hub_callback,  # Fixed name
        )
        self.workspace.show()
        self.close()

    def _open_store(self):
        """Tells the main Controller that the user wants to open the store."""
        self.open_store_callback(self)

    def _open_ai_chat(self):
        """Show the floating AI Chat window from the Hub."""
        if self._ai_window is None:
            self._ai_window = AIChatWindow(parent=self, current_module_id=None)
        self._ai_window.show()
        self._ai_window.raise_()
        self._ai_window.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scale = max(1.0, min(self.width() / 800.0, 1.8))

        try:
            # Increase DNA size but keep it centered
            # We increase the 'box' so the fade has room to reach 0 alpha
            anim_sz = int(320 * scale)  # Increased from 180
            self.animation_widget.setFixedSize(anim_sz, anim_sz)

            # Update Title & Subtitle Colors (This forces them to re-read the theme)
            self.lbl_title.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: {int(42 * scale)}px; font-weight: 900;"
            )
            self.lbl_subtitle.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: {int(16 * scale)}px; font-weight: bold;"
            )
            self.lbl_desc.setStyleSheet(
                f"color: {Colors.FG_SECONDARY}; font-size: {int(13 * scale)}px;"
            )

            # Update the Window Background itself
            self.setStyleSheet(f"QMainWindow {{ background-color: {Colors.BG_DARKEST}; }}")
        except AttributeError:
            pass

    def closeEvent(self, event):
        """Save window geometry before closing."""
        from biopro.core.preferences import core_preferences

        geom_hex = self.saveGeometry().toHex().data().decode("ascii")
        core_preferences.set("hub_window_geometry", geom_hex)
        super().closeEvent(event)

    def refresh_ui(self):
        """The Hub doesn't display module buttons natively, so we pass."""
        pass

    def _setup_menu_bar(self):
        """Adds the Theme menu to the Hub so you can switch before entering a project."""
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("&Theme")

        # DYNAMIC THEME DISCOVERY
        available_themes = theme_manager.discover_themes()
        for name, path in available_themes:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=path: self._switch_theme(p))
            theme_menu.addAction(action)

    def _switch_theme(self, theme_path: Path):
        theme_manager.load_theme(theme_path)
        from biopro.core.preferences import core_preferences

        core_preferences.set("theme", str(theme_path.absolute()))

    def _on_theme_changed(self):
        """Refreshes the Hub visuals when the theme changes."""
        self._apply_theme_styles()
        if hasattr(self, "left_panel"):
            self.left_panel.setStyleSheet(
                f"background-color: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};"
            )
        if hasattr(self, "lbl_recent"):
            self.lbl_recent.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: 14px; font-weight: bold; border: none;"
            )
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: 42px; font-weight: 900; letter-spacing: 1px;"
            )
        if hasattr(self, "lbl_badge"):
            self.lbl_badge.setStyleSheet(
                f"color: {Colors.ACCENT_PRIMARY}; background: transparent; "
                f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; "
                f"padding: 2px 6px; font-size: 10px; font-weight: bold; margin-top: 15px;"
            )
        if hasattr(self, "lbl_subtitle"):
            self.lbl_subtitle.setStyleSheet(
                f"color: {Colors.FG_PRIMARY}; font-size: 16px; font-weight: bold;"
            )
        if hasattr(self, "lbl_desc"):
            self.lbl_desc.setStyleSheet(
                f"color: {Colors.FG_SECONDARY}; font-size: 13px; margin-bottom: 20px;"
            )
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
        if hasattr(self, "list_recent"):
            self.list_recent.setStyleSheet(
                f"QListWidget {{ border: none; background: transparent; color: {Colors.FG_SECONDARY}; }}"
                f"QListWidget::item {{ padding: 10px; border-radius: 5px; }}"
                f"QListWidget::item:hover {{ background: {Colors.BG_MEDIUM}; }}"
                f"QListWidget::item:selected {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; font-weight: bold; }}"
            )


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
            panel_class = mod.CytoMetricsPanel  # Adjust to your dynamic loading logic

            # We can't actually instantiate QWidgets in a background thread without
            # making PyQt angry, so we just import the heavy libraries and
            # pass the Class reference back to the main thread to be built instantly.

            self.finished.emit((panel_class, self.workflow_data))

        except Exception as e:
            self.error.emit(str(e))


class _UpdateCheckWorker(QThread):
    """Background worker that runs the update check without blocking the Hub UI.

    Calls UpdateChecker.check_and_notify() on a worker thread. If an update is
    found, UpdateChecker emits the event bus signal which is automatically
    marshalled back to the main thread (Qt signal safety) and triggers the banner.
    """

    def __init__(self, update_checker):
        super().__init__()
        self._update_checker = update_checker

    def run(self) -> None:
        """Execute the update check on the background thread."""
        self._update_checker.check_and_notify()
