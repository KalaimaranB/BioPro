"""BioPro Hub - Project selection and creation dashboard."""

import logging
from pathlib import Path

from biopro_sdk.plugin import PrimaryButton, SecondaryButton
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QKeySequence,
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

        # Show the core intro tutorial on first ever launch (800ms delay lets
        # the window fully render before the overlay appears)
        QTimer.singleShot(800, self._maybe_start_core_intro)

        # Lightweight polling loop to keep the overlay in sync with AcademyManager
        self._hub_poll_timer = QTimer(self)
        self._hub_poll_timer.setInterval(100)
        self._hub_poll_timer.timeout.connect(self._poll_tutorial_overlay)
        self._hub_poll_timer.start()

    def _setup_ui(self) -> None:
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        # Tutorial overlay — parented to the central widget so it floats over
        # the entire hub window.  Created early so _maybe_start_core_intro can
        # reference it immediately after the 800 ms delay.
        from biopro.ui.wizards.tutorial_overlay import TutorialOverlay

        self._hub_tutorial_overlay = TutorialOverlay(self._central_widget, compact_mode=True)
        self._hub_tutorial_overlay.hide()
        self._hub_tutorial_overlay.btn_next.clicked.connect(self._on_hub_tutorial_next)
        self._hub_tutorial_overlay.btn_close.clicked.connect(self._on_hub_tutorial_skip)

        # Outer vertical layout: banner on top, main panels below
        outer_layout = QVBoxLayout(self._central_widget)
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
        self.list_recent.setObjectName("list_recent")
        self.list_recent.setStyleSheet(
            f"QListWidget {{ border: none; background: transparent; color: {Colors.FG_SECONDARY}; }}"
            f"QListWidget::item {{ padding: 10px; border-radius: 5px; }}"
            f"QListWidget::item:hover {{ background: {Colors.BG_MEDIUM}; }}"
            f"QListWidget::item:selected {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; font-weight: bold; }}"
        )
        self.list_recent.itemDoubleClicked.connect(self._on_recent_double_clicked)
        self.list_recent.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_recent.customContextMenuRequested.connect(self._on_recent_context_menu)
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
        self.btn_new.setProperty("tutorial_id", "btn_new")
        self.btn_new.clicked.connect(self._on_new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_open = SecondaryButton("📁 Open Project...")
        self.btn_open.setObjectName("btn_open")
        self.btn_open.clicked.connect(self._on_open_project)
        btn_layout.addWidget(self.btn_open)

        right_layout.addLayout(btn_layout)
        main_layout.addWidget(right_panel)

    # ── Tutorial overlay helpers ────────────────────────────────────────
    def _maybe_start_core_intro(self) -> None:
        """Start the onboarding tour if the user hasn't seen it yet."""
        from biopro.core.preferences import core_preferences
        from biopro.core.tutorial_manager import global_tutorial_manager

        if global_tutorial_manager.is_core_intro_done():
            return
        if core_preferences.get("core_intro_dismissed_once", False):
            return

        started = global_tutorial_manager.start_core_intro()
        if started:
            self._sync_hub_overlay_geometry()
            self._hub_tutorial_overlay.show()
            # Trigger compact Cyto+bubble side-by-side positioning
            self._hub_tutorial_overlay.set_targets([])
            self._hub_tutorial_overlay.raise_()

    def _sync_hub_overlay_geometry(self) -> None:
        """Keep the overlay filling the central widget."""
        if hasattr(self, "_central_widget"):
            self._hub_tutorial_overlay.setGeometry(self._central_widget.rect())

    def _poll_tutorial_overlay(self) -> None:
        """Lightweight timer slot: re-renders the overlay when the step changes."""
        from biopro.core.tutorial_manager import global_tutorial_manager

        if not self._hub_tutorial_overlay.isVisible():
            return

        step = global_tutorial_manager.current_step
        if not step:
            self._hub_tutorial_overlay.hide()
            return

        self._sync_hub_overlay_geometry()

        # Only re-render when the step actually changes
        if step.id != getattr(self, "_hub_last_step_id", None):
            self._hub_last_step_id = step.id
            self._hub_tutorial_overlay.render_step(step)

        # Always update target rectangles to track widget movement
        targets = []
        if getattr(step, "target_widget_names", []):
            for name in step.target_widget_names:
                # First try objectName match
                by_name = [w for w in self.findChildren(QWidget, name) if w and w.isVisible()]
                if by_name:
                    targets.extend(by_name)
                else:
                    # Fall back to tutorial_id property match
                    for w in self.findChildren(QWidget):
                        if w.property("tutorial_id") == name and w.isVisible():
                            targets.append(w)

        rects = []
        for w in targets:
            global_pos = w.mapToGlobal(w.rect().topLeft())
            local_pos = self._hub_tutorial_overlay.mapFromGlobal(global_pos)
            from PyQt6.QtCore import QRect

            rects.append(QRect(local_pos, w.size()))

        self._hub_tutorial_overlay.set_targets(rects)
        self._hub_tutorial_overlay.raise_()

    def _on_hub_tutorial_next(self) -> None:
        from biopro.core.models.tutorial_models import BranchingStep
        from biopro.core.tutorial_manager import global_tutorial_manager

        step = global_tutorial_manager.current_step

        if step and isinstance(step, BranchingStep):
            first_target = next(iter(step.options.values()), None)
            if first_target == "__complete__":
                global_tutorial_manager.complete_course()
                global_tutorial_manager.current_step = None
                global_tutorial_manager._emit_step_changed()
            elif first_target:
                global_tutorial_manager.next_step(first_target)
            return

        global_tutorial_manager.next_step()

    def _on_hub_tutorial_skip(self) -> None:
        from biopro.core.preferences import core_preferences
        from biopro.core.tutorial_manager import global_tutorial_manager

        core_preferences.set("core_intro_dismissed_once", True)
        global_tutorial_manager.active_course = None
        global_tutorial_manager.current_step = None
        self._hub_tutorial_overlay.hide()

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
        """Deprecated — Academy courses are now accessed per-workflow inside the Workspace.

        This method is kept for internal compatibility but should no longer be
        called from the UI. Open a project normally and use the 🎓 Academy button
        inside the Workspace toolbar instead.
        """
        logger.warning("_on_academy_project() is deprecated. Academy courses are now per-workflow.")

    def _on_open_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select BioPro Project Folder")
        if not dir_path:
            return

        self._attempt_open(Path(dir_path))

    def _on_recent_double_clicked(self, item: QListWidgetItem):
        path_str = item.data(Qt.ItemDataRole.UserRole)
        if path_str:
            self._attempt_open(Path(path_str))

    def _on_recent_context_menu(self, pos):
        import shutil

        from PyQt6.QtWidgets import QMenu

        from biopro.core.config import AppConfig

        item = self.list_recent.itemAt(pos)
        if not item:
            return

        path_str = item.data(Qt.ItemDataRole.UserRole)
        if not path_str:
            return

        menu = QMenu(self)
        action_remove = menu.addAction("Remove from Recent List")
        action_delete = menu.addAction("Delete Project from Disk...")

        action = menu.exec(self.list_recent.mapToGlobal(pos))
        if not action:
            return

        config = AppConfig()
        if action == action_remove:
            config.remove_recent_project(path_str)
            self._load_recent_projects()
        elif action == action_delete:
            reply = QMessageBox.warning(
                self,
                "Delete Project",
                f"Are you sure you want to permanently delete the project at:\n\n{path_str}\n\nThis cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Remove from recents list first
                    config.remove_recent_project(path_str)

                    # Delete from disk
                    target_path = Path(path_str)
                    if target_path.exists() and target_path.is_dir():
                        shutil.rmtree(target_path)

                    self._load_recent_projects()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete project:\n{str(e)}")

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
        from biopro.core.event_bus import BioProEvent, event_bus

        # 1. Save to global recents list
        config = AppConfig()
        config.add_recent_project(project_manager.project_dir)

        # 2. Emit PROJECT_LOADED so WaitForEventStep(PROJECT_LOADED) auto-advances
        event_bus.emit(BioProEvent.PROJECT_LOADED, str(project_manager.project_dir))

        # 3. Transition the UI
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
        from biopro.core.event_bus import BioProEvent, event_bus

        event_bus.emit(BioProEvent.STORE_OPENED)
        self.open_store_callback(self)
        # STORE_CLOSED is emitted by the controller/store dialog when it closes
        event_bus.emit(BioProEvent.STORE_CLOSED)

    def _open_ai_chat(self):
        """Show the floating AI Chat window from the Hub."""
        if self._ai_window is None:
            self._ai_window = AIChatWindow(parent=self, current_module_id=None)
        self._ai_window.show()
        self._ai_window.raise_()
        self._ai_window.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_hub_overlay_geometry()
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
        self._hub_poll_timer.stop()
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

        # HELP MENU
        help_menu = menubar.addMenu("&Help")

        docs_action = QAction("📖 BioPro &Help Center", self)
        docs_action.setShortcut(QKeySequence("F1"))
        docs_action.triggered.connect(self._open_help_center)
        help_menu.addAction(docs_action)

        help_menu.addSeparator()

        wiki_action = QAction("🌐 View GitHub Wiki Online", self)
        wiki_action.triggered.connect(self._open_wiki_online)
        help_menu.addAction(wiki_action)

        about_action = QAction("🧬 &About BioPro", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        help_menu.addSeparator()

        restart_tour_action = QAction("♻️ Restart Onboarding Tour", self)
        restart_tour_action.triggered.connect(self._restart_core_intro)
        help_menu.addAction(restart_tour_action)

    def _open_help_center(self):
        """Launch the localized help center."""
        from biopro.ui.dialogs.help_dialog import HelpCenterDialog

        dialog = HelpCenterDialog(module_manager=self.module_manager, parent=self)
        dialog.exec()

    def _open_wiki_online(self):
        """Open the public wiki in the browser."""
        import webbrowser

        webbrowser.open("https://github.com/KalaimaranB/BioPro/wiki")

    def _restart_core_intro(self) -> None:
        """Resets core intro progress and re-launches the onboarding tour."""
        from biopro.core.preferences import core_preferences
        from biopro.core.tutorial_manager import global_tutorial_manager

        # Clear both gates so the tour auto-starts again
        global_tutorial_manager.reset_course("core_intro_v1")
        core_preferences.set("core_intro_dismissed_once", False)

        self._maybe_start_core_intro()

    def _show_about(self) -> None:
        from biopro.core.config import AppConfig

        QMessageBox.about(
            self,
            "About BioPro",
            f"<h2>🧬 BioPro v{AppConfig.CORE_VERSION}</h2>"
            "<p>Bio Analysis Made Simple</p>"
            "<p>An open-source, intuitive platform for lab students "
            "and professionals.</p>"
            "<p>© 2026 BioPro Contributors<br>"
            "Licensed under the MIT License</p>",
        )

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
