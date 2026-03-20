"""Main application window for BioPro.

Navigation flow:
    Home Screen  →  Analysis View  (Dynamically loaded modules)
"""

from __future__ import annotations

import logging
from PyQt6.QtGui import QAction, QKeySequence  # <-- Add QKeySequence here

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.home_screen import HomeScreen
from biopro.core.config import AppConfig
from biopro.ui.theme import Colors, Fonts, theme_manager
from biopro.shared.ui.ui_components import SecondaryButton

logger = logging.getLogger(__name__)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

_PAGE_HOME = 0
_PAGE_ANALYSIS = 1


class AnalysisToolBar(QWidget):
    """Slim contextual toolbar shown above the analysis splitter."""

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("analysisToolBar")
        self.setStyleSheet(
            f"QWidget#analysisToolBar {{"
            f"  background: {Colors.BG_DARK};"
            f"  border-bottom: 1px solid {Colors.BORDER};"
            f"}}"
        )
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 14, 0)
        layout.setSpacing(8)

        # Look how clean this is using our SDK!
        self.btn_close_project = SecondaryButton("🏠 Return to Hub")
        layout.addWidget(self.btn_close_project)

        self.btn_home = SecondaryButton("← Home")
        layout.addWidget(self.btn_home)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(sep)

        self.title_lbl = QLabel(f"🔬  {title}")
        self.title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600;"
            f" color: {Colors.FG_PRIMARY}; background: transparent;"
        )
        layout.addWidget(self.title_lbl)
        layout.addStretch()

        self.lbl_hint = QLabel("Ctrl+O to open image")
        self.lbl_hint.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_DISABLED};"
            f" background: transparent;"
        )
        layout.addWidget(self.lbl_hint)

    def set_title(self, icon: str, name: str) -> None:
        self.title_lbl.setText(f"{icon}  {name}")


class MainWindow(QMainWindow):
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
        self._connect_signals()

        # Populate the Home Screen with dynamic modules
        self.home_screen.populate_modules(self.module_manager.get_available_modules())

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
            app.setStyleSheet(app.styleSheet() + extra)

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
        
        help_menu = menubar.addMenu("&Help")
        about_action = QAction("&About BioPro", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_central_widget(self) -> None:
        self.root_stack = QStackedWidget()

        # ── Page 0: Home ──────────────────────────────────────────────
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

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.wizard_panel = None
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_container.setMinimumWidth(360)
        self.left_container.setMaximumWidth(560)

        self._right_container = QWidget()
        self.right_layout = QVBoxLayout(self._right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_container.setMinimumWidth(300)
        self._right_container.hide()

        self.splitter.addWidget(self.left_container)
        self.center_container = QWidget()
        self.center_layout = QVBoxLayout(self.center_container)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.center_container)
        self.splitter.addWidget(self._right_container)
        self.splitter.setSizes([420, 980, 0])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)

        ap_layout.addWidget(self.splitter, stretch=1)
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
        

    def _show_home(self) -> None:
        if self.wizard_panel and hasattr(self.wizard_panel, 'reset_to_setup'):
            self.wizard_panel.reset_to_setup()
        self.root_stack.setCurrentIndex(_PAGE_HOME)
        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")
        self.zoom_label.setText("")

    def _open_module(self, manifest: dict) -> None:
        module_id = manifest["id"]
        self.current_module_id = module_id

        try:
            PanelClass = self.module_manager.load_module_ui(module_id)

            if self.wizard_panel is not None:
                self.wizard_panel.setParent(None)
                self.wizard_panel.deleteLater()

            self.wizard_panel = PanelClass()
            self.wizard_panel.project_manager = self.project_manager

            # 1. Add Left Panel (The Wizard)
            self.left_layout.addWidget(self.wizard_panel)

            # 2. Clear and Add Center Panel (The Canvas)
            # (Assuming you have a self.center_layout where the canvas used to be. 
            # If you add directly to the splitter, use self.splitter.insertWidget(1, center_widget))
            while hasattr(self, 'center_layout') and self.center_layout.count():
                item = self.center_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            if hasattr(self.wizard_panel, 'get_center_widget'):
                center_widget = self.wizard_panel.get_center_widget()
                if center_widget and hasattr(self, 'center_layout'):
                    self.center_layout.addWidget(center_widget)

                    if hasattr(center_widget, 'zoom_changed') and hasattr(self, 'zoom_label'):
                        center_widget.zoom_changed.connect(
                            lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
                        )

            # 3. Clear and Add Right Panel (The Results)
            while self.right_layout.count():
                item = self.right_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            if hasattr(self.wizard_panel, 'get_right_panel_widget'):
                right_widget = self.wizard_panel.get_right_panel_widget()
                if right_widget:
                    self.right_layout.addWidget(right_widget)

            self.analysis_toolbar.set_title(manifest.get("icon", "📦"), manifest.get("name", "Analysis"))

            # --- THE PLUGIN NOW MANAGES ITS OWN CANVAS SIGNALS ---
            # We ONLY connect universal UI signals here
            if hasattr(self.wizard_panel, 'status_message'):
                self.wizard_panel.status_message.connect(self.status_bar.showMessage)
            if hasattr(self.wizard_panel, 'results_ready'):
                self.wizard_panel.results_ready.connect(self._reveal_right_panel)
            if hasattr(self.wizard_panel, 'state_changed'):
                self.wizard_panel.state_changed.connect(self._push_history)

            self.root_stack.setCurrentIndex(_PAGE_ANALYSIS)
            self.status_bar.showMessage(f"{manifest.get('name')} — open an image to begin (Ctrl+O)")

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Module Error", f"Failed to load module {module_id}:\n{str(e)}")
            logger.exception(f"Failed to load module {module_id}")

    def _reveal_right_panel(self, *args) -> None:
        if self._right_container.isHidden():
            self._right_container.show()
            total = self.splitter.width()
            left = 340
            right = max(320, total // 4)
            centre = max(200, total - left - right)
            self.splitter.setSizes([left, centre, right])

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
        if hasattr(self, 'project_manager') and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        super().closeEvent(event)

    def return_to_hub(self):
        # 1. Cleanly close the active project
        if hasattr(self, 'project_manager') and self.project_manager:
            try:
                self.project_manager.close()
                self.project_manager = None 
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        
        # 2. Ask the Controller to open the Hub!
        self.return_to_hub_callback()
        
        # 3. Destroy this window
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

    def _on_theme_changed(self) -> None:
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        self._apply_supplemental_qss()
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