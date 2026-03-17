"""Main application window for BioPro.

Navigation flow:
    Home Screen  →  Analysis View  (Dynamically loaded modules)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.home_screen import HomeScreen
from biopro.shared.ui.image_canvas import ImageCanvas
from biopro.shared.ui.results_widget import ResultsWidget
from biopro.core.project_manager import ProjectManager
from biopro.ui.theme import Colors, Fonts

logger = logging.getLogger(__name__)

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

        self.btn_close_project = QPushButton("🏠 Return to Hub")
        self.btn_close_project.setStyleSheet(
            f"QPushButton {{"
            f"  background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER};"
            f"  border-radius: 5px; padding: 3px 10px;"
            f"  color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f"}}"
        )
        layout.addWidget(self.btn_close_project)

        self.btn_home = QPushButton("← Home")
        self.btn_home.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: 1px solid {Colors.BORDER};"
            f"  border-radius: 5px; padding: 3px 10px;"
            f"  color: {Colors.FG_SECONDARY}; font-size: {Fonts.SIZE_SMALL}px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};"
            f"}}"
        )
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

    def __init__(self, project_manager: ProjectManager, module_manager, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.module_manager = module_manager
        
        project_name = self.project_manager.data.get("project_name", "Untitled Project")
        self.setWindowTitle(f"BioPro Workspace — {project_name}")
        self.setMinimumSize(1200, 800)

        self._apply_supplemental_qss()
        self.resize(self.DEFAULT_SIZE)

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

        # Populate the Home Screen with dynamic modules
        self.home_screen.populate_modules(self.module_manager.get_available_modules())

        self._show_home()

    def _apply_supplemental_qss(self) -> None:
        from PyQt6.QtWidgets import QApplication
        from biopro.ui.theme import Colors
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
        )
        app = QApplication.instance()
        if app:
            app.setStyleSheet(app.styleSheet() + extra)

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

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

        # Left container starts empty and waits for a module click
        self.wizard_panel = None
        self.left_container = QWidget()
        self.left_layout = QVBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_container.setMinimumWidth(360)
        self.left_container.setMaximumWidth(560)

        self.canvas = ImageCanvas()

        self.results_widget = ResultsWidget()
        self._right_container = QWidget()
        right_layout = QVBoxLayout(self._right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.results_widget)
        self._right_container.setMinimumWidth(300)
        self._right_container.hide()

        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.canvas)
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
        self.canvas.zoom_changed.connect(
            lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
        )

    def _show_home(self) -> None:
        if self.wizard_panel and hasattr(self.wizard_panel, 'reset_to_setup'):
            self.wizard_panel.reset_to_setup()
        self.root_stack.setCurrentIndex(_PAGE_HOME)
        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")
        self.zoom_label.setText("")

    def _open_module(self, manifest: dict) -> None:
        module_id = manifest["id"]

        try:
            PanelClass = self.module_manager.load_module_ui(module_id)

            if self.wizard_panel is not None:
                self.wizard_panel.setParent(None)
                self.wizard_panel.deleteLater()

            self.wizard_panel = PanelClass()
            self.wizard_panel.project_manager = self.project_manager

            self.left_layout.addWidget(self.wizard_panel)

            self.analysis_toolbar.set_title(manifest.get("icon", "📦"), manifest.get("name", "Analysis"))

            if hasattr(self.wizard_panel, 'set_canvas'):
                self.wizard_panel.set_canvas(self.canvas)
            if hasattr(self.wizard_panel, 'set_results_widget'):
                self.wizard_panel.set_results_widget(self.results_widget)
            
            self.results_widget.set_canvas(self.canvas)

            # Reconnect dynamic signals
            self.wizard_panel.image_changed.connect(self.canvas.set_image)
            self.wizard_panel.status_message.connect(self.status_bar.showMessage)
            
            if hasattr(self.wizard_panel, 'lanes_detected'):
                self.wizard_panel.lanes_detected.connect(lambda lanes: self.canvas.add_lane_overlays(lanes))
            if hasattr(self.wizard_panel, 'bands_detected'):
                self.wizard_panel.bands_detected.connect(lambda bands, lanes: self.canvas.add_band_overlays(lanes, bands))
            if hasattr(self.wizard_panel, 'peak_picking_enabled'):
                self.wizard_panel.peak_picking_enabled.connect(self.canvas.set_peak_picking_enabled)
            if hasattr(self.wizard_panel, 'crop_mode_toggled'):
                self.wizard_panel.crop_mode_toggled.connect(self.canvas.set_crop_mode)
            if hasattr(self.wizard_panel, 'profile_hovered'):
                self.wizard_panel.profile_hovered.connect(self._on_profile_hovered)
            if hasattr(self.wizard_panel, 'results_ready'):
                self.wizard_panel.results_ready.connect(self._on_results_ready)
            if hasattr(self.wizard_panel, 'selected_bands_changed'):
                self.wizard_panel.selected_bands_changed.connect(self.results_widget.update_pairwise_comparison)

            # Canvas -> Wizard reconnects
            try: self.canvas.band_clicked.disconnect() 
            except: pass
            self.canvas.band_clicked.connect(self.wizard_panel.on_band_clicked)
            
            try: self.canvas.peak_pick_requested.disconnect()
            except: pass
            self.canvas.peak_pick_requested.connect(self.wizard_panel.on_peak_pick_requested)
            
            try: self.canvas.crop_requested.disconnect()
            except: pass
            self.canvas.crop_requested.connect(self.wizard_panel.on_crop_requested)

            self.root_stack.setCurrentIndex(_PAGE_ANALYSIS)
            self.status_bar.showMessage(f"{manifest.get('name')} — open an image to begin (Ctrl+O)")

        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Module Error", f"Failed to load module {module_id}:\n{str(e)}")
            logger.exception(f"Failed to load module {module_id}")

    def _on_results_ready(self, df) -> None:
        self.wizard_panel.set_results_widget(self.results_widget)
        self.results_widget.set_results(df)
        if self._right_container.isHidden():
            self._right_container.show()
            total = self.splitter.width()
            left = 340
            right = max(320, total // 4)
            centre = max(200, total - left - right)
            self.splitter.setSizes([left, centre, right])

    def _on_profile_hovered(self, lane_idx: int, y_pos: float) -> None:
        lanes = getattr(self.wizard_panel.analyzer.state, "lanes", [])
        if not lanes or lane_idx < 0 or lane_idx >= len(lanes):
            self.canvas.hide_hover_indicator()
            return
        if y_pos < 0:
            self.canvas.hide_hover_indicator()
            return
        lane = lanes[lane_idx]
        self.canvas.show_hover_indicator(lane, lane.y_start + float(y_pos))

    def _on_open_file(self) -> None:
        if self.root_stack.currentIndex() == _PAGE_HOME:
            self.status_bar.showMessage("Please select an analysis module first.")
            return
        if self.wizard_panel and hasattr(self.wizard_panel, '_open_file'):
            self.wizard_panel._open_file()

    def _show_about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About BioPro",
            "<h2>🧬 BioPro v0.1.0</h2>"
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
                import logging
                logging.getLogger(__name__).error(f"Error closing project: {e}")
        super().closeEvent(event)

    def return_to_hub(self):
        if hasattr(self, 'project_manager') and self.project_manager:
            try:
                self.project_manager.close()
                self.project_manager = None 
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error closing project: {e}")
        
        from biopro.ui.hub_window import HubWindow
        self.hub_window = HubWindow()
        self.hub_window.show()
        self.close()

    def _open_store(self):
        from biopro.ui.store_dialog import StoreDialog
        dialog = StoreDialog(self.module_manager, self)
        dialog.exec()