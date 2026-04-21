"""Workspace Window for BioPro."""

from __future__ import annotations
import logging
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QSplitter, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
    QGraphicsOpacityEffect
)

from biopro.ui.dashboards.workspace_dashboard import WorkspaceDashboard as HomeScreen
from biopro.core.config import AppConfig
from biopro.ui.theme import Colors, Fonts, theme_manager
from biopro.core.event_bus import event_bus, BioProEvent
from biopro.sdk.ui import SecondaryButton
from biopro.ui.components.toolbars import AnalysisToolBar

logger = logging.getLogger(__name__)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

_PAGE_HOME = 0
_PAGE_ANALYSIS = 1

class WorkspaceWindow(QMainWindow):
    """BioPro main application window."""

    APP_TITLE = "BioPro — Bio-Image Analysis"
    DEFAULT_SIZE = QSize(1400, 860)

    # Added hub_callback to the signature!
    def __init__(self, project_manager, module_manager, updater, store_callback, hub_callback):
        super().__init__()
        self.project_manager = project_manager
        self.module_manager = module_manager
        self.updater = updater
        self.open_store_callback = store_callback
        self.return_to_hub_callback = hub_callback 
        
        project_name = self.project_manager.data.get("project_name", "Untitled Project")
        self.setWindowTitle(f"BioPro Workspace — {project_name}")
        self.setMinimumSize(1200, 800)

        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")

        self._apply_supplemental_qss()
        self.resize(self.DEFAULT_SIZE)

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._setup_shortcuts()
        self._connect_signals()
        
        # Connect to the core's nervous system (The Event Bus)
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, lambda _: self.refresh_ui())
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, lambda _: self.refresh_ui())

        # Populate the Home Screen with dynamic modules
        self.home_screen.populate_modules(self.module_manager.get_available_modules())
        self._refresh_hub_workflows()

        self._show_home()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _apply_supplemental_qss(self) -> None:
        from PyQt6.QtWidgets import QApplication
        extra = (
            "QCheckBox { spacing: 8px; color: #e6edf3; }"
            f"QCheckBox::indicator {{ width: 16px; height: 16px;"
            f" border: 2px solid {Colors.BORDER_FOCUS}; border-radius: 4px;"
            f" background: {Colors.BG_MEDIUM}; }}"
            f"QCheckBox::indicator:checked {{ background: {Colors.ACCENT_PRIMARY};"
            f" border-color: {Colors.ACCENT_PRIMARY}; }}"
            f"QCheckBox::indicator:unchecked:hover {{ border-color: {Colors.FG_SECONDARY}; }}"
            f"QCheckBox::indicator:disabled {{ border-color: {Colors.BG_LIGHT};"
            f" background: {Colors.BG_DARK}; }}"
            f"QGroupBox {{ color: {Colors.FG_PRIMARY}; font-weight: bold; "
            f" border: 1px solid {Colors.BORDER}; border-radius: 6px; margin-top: 12px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 5px; }}"
            f"QRadioButton {{ color: {Colors.FG_PRIMARY}; }}"
            f"QLabel {{ color: {Colors.FG_PRIMARY}; }}"
            f"QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {{"
            f"  background-color: {Colors.BG_DARKEST};"
            f"  color: {Colors.FG_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: 4px;"
            f"  padding: 4px 8px;"
            f"}}"
            f"QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {{"
            f"  border: 1px solid {Colors.BORDER_FOCUS};"
            f"  background-color: {Colors.BG_DARK};"
            f"}}"
            f"QSpinBox::up-button, QDoubleSpinBox::up-button {{"
            f"  subcontrol-origin: border; subcontrol-position: top right; width: 16px; border: none;"
            f"}}"
            f"QSpinBox::down-button, QDoubleSpinBox::down-button {{"
            f"  subcontrol-origin: border; subcontrol-position: bottom right; width: 16px; border: none;"
            f"}}"
            f"QGraphicsView {{"
            f"  border: 1px solid {Colors.BORDER};"
            f"  background-color: {Colors.BG_DARKEST};"
            f"}}"
        )
        app = QApplication.instance()
        if app:
            app.setStyleSheet("")
            app.setStyleSheet(extra)

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        # --- Edit Menu for History ---
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        # Magic cross-platform native Undo shortcut
        undo_action.setShortcut(QKeySequence.StandardKey.Undo) 
        undo_action.triggered.connect(self.trigger_undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        # Magic cross-platform native Redo shortcut
        redo_action.setShortcut(QKeySequence.StandardKey.Redo) 
        redo_action.triggered.connect(self.trigger_redo)
        edit_menu.addAction(redo_action)
        # -----------------------------

        open_action = QAction("&Open Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()

        home_action = QAction("&Home Screen", self)
        home_action.setShortcut("Ctrl+H")
        home_action.triggered.connect(self._show_home)
        file_menu.addAction(home_action)
        file_menu.addSeparator()

        close_project_action = QAction("Close Project && Return to Hub", self)
        close_project_action.triggered.connect(self.return_to_hub)
        file_menu.addAction(close_project_action)

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        theme_menu = menubar.addMenu("&Theme")
        
        action_default = QAction("BioPro Default", self)
        action_default.triggered.connect(lambda: self._switch_theme("default.json"))
        theme_menu.addAction(action_default)
        
        action_sw = QAction("Star Wars (Dark Side)", self)
        action_sw.triggered.connect(lambda: self._switch_theme("star_wars.json"))
        theme_menu.addAction(action_sw)

        # Help Menu
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

    def _setup_shortcuts(self):
        """Register global app shortcuts."""
        help_shortcut = QAction(self)
        help_shortcut.setShortcut(QKeySequence("F1"))
        help_shortcut.triggered.connect(self._open_help_center)
        self.addAction(help_shortcut)

    def _open_help_center(self):
        """Launch the localized help center."""
        from biopro.ui.dialogs.help_dialog import HelpCenterDialog
        dialog = HelpCenterDialog(module_manager=self.module_manager, parent=self)
        dialog.exec()

    def _open_wiki_online(self):
        """Open the public wiki in the browser."""
        import webbrowser
        webbrowser.open("https://github.com/KalaimaranB/BioPro/wiki")
    def _setup_central_widget(self) -> None:
        self.root_stack = QStackedWidget()

        # ── Page 0: Hub (Tabbed View) ──────────────────────────────────
        self.home_screen = HomeScreen()
        self.root_stack.addWidget(self.home_screen)

        # ── Page 1: Analysis view ─────────────────────────────────────
        analysis_page = QWidget()
        analysis_page.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        ap_layout = QVBoxLayout(analysis_page)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.setSpacing(0)

        self.analysis_toolbar = AnalysisToolBar("Analysis")
        self.analysis_toolbar.btn_home.clicked.connect(self._show_home)
        self.analysis_toolbar.btn_close_project.clicked.connect(self.return_to_hub)
        ap_layout.addWidget(self.analysis_toolbar)

        self.wizard_panel = None
        self.main_module_container = QWidget()
        self.main_module_layout = QVBoxLayout(self.main_module_container)
        self.main_module_layout.setContentsMargins(0, 0, 0, 0)

        ap_layout.addWidget(self.main_module_container, stretch=1)
        self.root_stack.addWidget(analysis_page)

        self.setCentralWidget(self.root_stack)

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("subtitle")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")

    def _connect_signals(self) -> None:
        self.home_screen.module_selected.connect(self._open_module)
        self.home_screen.return_to_hub_requested.connect(self.return_to_hub)
        self.home_screen.open_store_requested.connect(self._open_store)
        
        # ── THE NEW WORKFLOW SIGNALS ──
        self.home_screen.workflow_selected.connect(self._load_workflow_from_dashboard)
        self.home_screen.workflow_delete_requested.connect(self._handle_delete_workflow)
        self.home_screen.trust_module_requested.connect(self._on_trust_requested)
        

    def _show_home(self) -> None:
        if self.wizard_panel and hasattr(self.wizard_panel, 'reset_to_setup'):
            self.wizard_panel.reset_to_setup()
            
        # THE FIX:
        self._transition_to_page(_PAGE_HOME) 
        
        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")
        self.zoom_label.setText("")

    def _open_module(self, manifest: dict) -> None:
        module_id = manifest["id"]
        self.current_module_id = module_id

        try:
            PanelClass = self.module_manager.load_module_ui(module_id)

            if self.wizard_panel is not None:
                # 1. Trigger the explicit lifecycle cleanup
                if hasattr(self.wizard_panel, "cleanup"):
                    self.wizard_panel.cleanup()
                
                self.wizard_panel.setParent(None)
                self.wizard_panel.deleteLater()

            self.wizard_panel = PanelClass()
            self.wizard_panel.project_manager = self.project_manager

            # Place the module directly into the main container
            self.main_module_layout.addWidget(self.wizard_panel)

            # Attempt to wire up zoom signals if the module exposes it (or a canvas object)
            if hasattr(self.wizard_panel, 'canvas') and hasattr(self.wizard_panel.canvas, 'zoom_changed'):
                self.wizard_panel.canvas.zoom_changed.connect(
                    lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
                )
            elif hasattr(self.wizard_panel, 'zoom_changed'):
                self.wizard_panel.zoom_changed.connect(
                    lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
                )

            self.analysis_toolbar.set_title(manifest.get("icon", "📦"), manifest.get("name", "Analysis"))

            # -- THE PLUGIN NOW MANAGES ITS OWN CANVAS SIGNALS ---
            if hasattr(self.wizard_panel, 'status_message'):
                self.wizard_panel.status_message.connect(self.status_bar.showMessage)
            if hasattr(self.wizard_panel, 'state_changed'):
                self.wizard_panel.state_changed.connect(self._push_history)

            # THE FIX:
            self._transition_to_page(_PAGE_ANALYSIS)
            
            self.status_bar.showMessage(f"{manifest.get('name')} — open an image to begin (Ctrl+O)")

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Module Error", f"Failed to load module {module_id}:\n{str(e)}")
            logger.exception(f"Failed to load module {module_id}")



    def _on_open_file(self) -> None:
        if self.root_stack.currentIndex() == _PAGE_HOME:
            self.status_bar.showMessage("Please select an analysis module first.")
            return
        if self.wizard_panel and hasattr(self.wizard_panel, '_open_file'):
            self.wizard_panel._open_file()

    def _show_about(self) -> None:
        # Dynamic Version from Config!
        QMessageBox.about(
            self,
            "About BioPro",
            f"<h2>🧬 BioPro v{AppConfig.CORE_VERSION}</h2>"
            "<p>Bio-Image Analysis Made Simple</p>"
            "<p>An open-source, intuitive alternative to ImageJ for lab "
            "students and professionals.</p>"
            "<p>© 2026 BioPro Contributors<br>"
            "Licensed under the MIT License</p>",
        )

    def closeEvent(self, event):
        """Ensures all projects and plugins release resources before exit."""
        # 1. Shutdown active plugin if any
        if hasattr(self, 'wizard_panel') and self.wizard_panel:
            try:
                if hasattr(self.wizard_panel, 'shutdown'):
                    self.wizard_panel.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin: {e}")

        # 2. Close project
        if hasattr(self, 'project_manager') and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        super().closeEvent(event)

    def return_to_hub(self):
        """Safely closes the active data and launches the main Project Hub window."""
        # 1. Cleanly clear the active project memory
        if hasattr(self, 'project_manager') and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        
        # 2. THE FIX: Wake up the external DNA Hub window!
        if hasattr(self, 'return_to_hub_callback') and self.return_to_hub_callback:
            self.return_to_hub_callback()
            
        # 3. THE FIX: Destroy this workspace window so it actually closes
        self.close()

    def _open_store(self):
        self.open_store_callback(self)
        
    def refresh_ui(self):
        """Hot-reloads the module UI after the Store is closed."""
        self.home_screen.populate_modules(self.module_manager.get_available_modules())

    def _switch_theme(self, filename: str) -> None:
        from pathlib import Path
        theme_path = Path(__file__).parent.parent.parent / "themes" / filename
        theme_manager.load_theme(theme_path)

    def _on_trust_requested(self, module_id: str) -> None:
        """Handle the user clicking the '⚠️ Lock' button on an untrusted plugin."""
        reply = QMessageBox.question(
            self,
            "Security: Trust Local Changes?",
            f"The module '{module_id}' has been modified locally.\n\n"
            "Do you trust these changes and want to lock them on this machine?\n\n"
            "By clicking 'Yes', BioPro will snapshot these files and trust them from now on.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.module_manager.trust_module(module_id):
                self.status_bar.showMessage(f"Permanently trusted local changes for {module_id}.", 5000)
                # Refresh dashboard
                self.home_screen.populate_modules(self.module_manager.get_available_modules())
            else:
                QMessageBox.critical(self, "Error", "Failed to trust module. Could not calculate hashes.")

    def _on_theme_changed(self) -> None:
        # Save where the user is currently looking!
        current_idx = self.root_stack.currentIndex()

        # 1. Update Main Window Base
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        self._apply_supplemental_qss()
        
        # 2. Update the Top Toolbar
        self.analysis_toolbar.setStyleSheet(
            f"QWidget#analysisToolBar {{"
            f"  background: {Colors.BG_DARK};"
            f"  border-bottom: 1px solid {Colors.BORDER};"
            f"}}"
        )
        self.analysis_toolbar.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600;"
            f" color: {Colors.FG_PRIMARY}; background: transparent;"
        )

        # 3. Update the Status Bar
        self.status_bar.setStyleSheet(
            f"background: {Colors.BG_DARK}; color: {Colors.FG_SECONDARY};"
            f" border-top: 1px solid {Colors.BORDER};"
        )

        # 4. Rebuild the Hub
        self.root_stack.removeWidget(self.home_screen)
        self.home_screen.deleteLater()
        
        self.home_screen = HomeScreen()
        
        # Rewire signals
        self.home_screen.module_selected.connect(self._open_module)
        self.home_screen.return_to_hub_requested.connect(self.return_to_hub)
        self.home_screen.open_store_requested.connect(self._open_store)
        self.home_screen.workflow_selected.connect(self._load_workflow_from_dashboard)
        self.home_screen.workflow_delete_requested.connect(self._handle_delete_workflow)
        
        # Insert back into stack at index 0
        self.root_stack.insertWidget(_PAGE_HOME, self.home_screen)
        self.home_screen.populate_modules(self.module_manager.get_available_modules())
        self._refresh_hub_workflows()

        # Update active module UI, if present
        if hasattr(self, 'wizard_panel') and self.wizard_panel is not None:
            if hasattr(self.wizard_panel, '_apply_theme_styles'):
                self.wizard_panel._apply_theme_styles()
            self.wizard_panel.update()
        
        # ── THE FIX: Restore the user's view so the screen doesn't go blank! ──
        self.root_stack.setCurrentIndex(current_idx)


    def _push_history(self):
        """Captures a snapshot of the active module and pushes it to RAM."""
        # Check if we actually have a module ID loaded
        if not self.wizard_panel or not hasattr(self.wizard_panel, "export_state") or not getattr(self, "current_module_id", None):
            return
            
        # Dynamically fetch the history for WHATEVER module is open!
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        history.push(self.wizard_panel.export_state())

    def trigger_undo(self):
        """Asks the HistoryManager to step back, then hands the old state to the plugin."""
        if not self.wizard_panel or not hasattr(self.wizard_panel, "load_state") or not getattr(self, "current_module_id", None):
            return
            
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        
        previous_state = history.undo()
        if previous_state is not None:
            self.wizard_panel.load_state(previous_state)
            self.status_bar.showMessage("Undid last action.")
        else:
            self.status_bar.showMessage("Nothing to undo.")

    def trigger_redo(self):
        """Asks the HistoryManager to step forward, then hands the state to the plugin."""
        if not self.wizard_panel or not hasattr(self.wizard_panel, "load_state") or not getattr(self, "current_module_id", None):
            return
            
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        
        next_state = history.redo()
        if next_state is not None:
            self.wizard_panel.load_state(next_state)
            self.status_bar.showMessage("Redid last action.")
        else:
            self.status_bar.showMessage("Nothing to redo.")
    def _refresh_hub_workflows(self) -> None:
        """Scans the project workflows folder and populates the dashboard."""
        workflows = []
        if self.project_manager and self.project_manager.project_dir:
            wf_dir = self.project_manager.project_dir / "workflows"
            if wf_dir.exists():
                import json
                # ── THE FIX: Use rglob to find ALL .json files, ignoring folder structure! ──
                for wf_file in wf_dir.rglob("*.json"):
                    try:
                        with open(wf_file, "r") as f:
                            data = json.load(f)
                            metadata = data.get("metadata", {})
                            workflows.append({
                                "filename": wf_file.name,
                                # Pull the module type directly from the file's saved metadata
                                "module_id": metadata.get("module", "western_blot"),
                                "name": metadata.get("name", wf_file.stem),
                                "timestamp": metadata.get("timestamp", "Unknown Date")
                            })
                    except Exception:
                        pass
                # ────────────────────────────────────────────────────────────────────────────
        
        # Sort newest first
        workflows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        self.home_screen.populate_workflows(workflows)
    
    def _load_workflow_from_dashboard(self, module_id: str, filename: str) -> None:
        """Handler for when a user clicks a workflow card in the Hub."""
        try:
            # 1. Load the payload 
            payload = self.project_manager.load_workflow_payload(filename)
            
            # 2. Find the manifest
            manifests = self.module_manager.get_available_modules()
            manifest = next((m for m in manifests if m["id"] == module_id), None)
            
            if not manifest:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Load Error", f"Module {module_id} is not currently installed.")
                return

            # 3. Open the module 
            self._open_module(manifest)
            
            # 4. Inject the payload
            if self.wizard_panel and hasattr(self.wizard_panel, "load_workflow"):
                self.wizard_panel.load_workflow(payload)
                self.status_bar.showMessage(f"Successfully loaded workflow: {filename}")
                
        except Exception as e:
            logger.exception("Failed to load workflow")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Load Error", f"Could not load workflow:\n{str(e)}")

    def _handle_delete_workflow(self, module_id: str, filename: str) -> None:
        success = self.project_manager.delete_workflow(module_id, filename)
        if success:
            # Refresh the UI so the card instantly vanishes!
            self._refresh_hub_workflows()

    # ─── ANIMATION ENGINE ───────────────────────────────────────────
    def _transition_to_page(self, page_index: int) -> None:
        """Smoothly fades out the current page and fades in the new one."""
        if self.root_stack.currentIndex() == page_index:
            return

        # 1. Attach an opacity effect to the entire window stack
        self._fade_effect = QGraphicsOpacityEffect(self.root_stack)
        self.root_stack.setGraphicsEffect(self._fade_effect)

        # 2. Animate the fade out (1.0 to 0.0)
        self._anim_out = QPropertyAnimation(self._fade_effect, b"opacity")
        self._anim_out.setDuration(150) # 150ms is the UI standard for snappy but smooth
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 3. When it hits absolute black, swap the page and trigger the fade in!
        self._anim_out.finished.connect(lambda: self._on_fade_out_finished(page_index))
        self._anim_out.start()

    def _on_fade_out_finished(self, page_index: int) -> None:
        """Triggers the fade-in sequence once the screen is black."""
        self.root_stack.setCurrentIndex(page_index)
        
        self._anim_in = QPropertyAnimation(self._fade_effect, b"opacity")
        self._anim_in.setDuration(150)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Remove the effect completely when done so it doesn't mess with text anti-aliasing!
        self._anim_in.finished.connect(lambda: self.root_stack.setGraphicsEffect(None))
        self._anim_in.start()
    # ────────────────────────────────────────────────────────────────