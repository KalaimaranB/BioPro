"""Main application window for BioPro.

Navigation flow:
    Home Screen  →  Analysis View  (Western Blot, or future modules)

Layout during analysis:
    ┌─────────────────────────────────────────────────┐
    │  ← Home  |  🔬 Western Blot Analysis   Menu Bar │
    ├──────────┬──────────────────────────────────────┤
    │          │                        │              │
    │  Wizard  │   Image Canvas         │  Results     │
    │  Panel   │   (zoom/pan)           │  (hidden     │
    │          │                        │  until step 4│
    │          │                        │  computes)   │
    ├──────────┴──────────────────────────────────────┤
    │                  Status Bar                      │
    └─────────────────────────────────────────────────┘

The wizard panel emits signals that update the canvas and results.
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
from biopro.ui.image_canvas import ImageCanvas
from biopro.ui.results_widget import ResultsWidget
from biopro.ui.western_blot_panel import WesternBlotPanel
from biopro.ui.theme import Colors, Fonts

logger = logging.getLogger(__name__)

_PAGE_HOME = 0
_PAGE_ANALYSIS = 1


class AnalysisToolBar(QWidget):
    """Slim contextual toolbar shown above the analysis splitter.

    Contains a '← Home' breadcrumb and the current module name.
    """

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

        title_lbl = QLabel(f"🔬  {title}")
        title_lbl.setStyleSheet(
            f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600;"
            f" color: {Colors.FG_PRIMARY}; background: transparent;"
        )
        layout.addWidget(title_lbl)
        layout.addStretch()

        self.lbl_hint = QLabel("Ctrl+O to open image")
        self.lbl_hint.setStyleSheet(
            f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_DISABLED};"
            f" background: transparent;"
        )
        layout.addWidget(self.lbl_hint)


class MainWindow(QMainWindow):
    """BioPro main application window."""

    APP_TITLE = "BioPro — Bio-Image Analysis"
    DEFAULT_SIZE = QSize(1400, 860)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(self.APP_TITLE)
        # Append supplemental QSS for widgets not covered by the base theme
        self._apply_supplemental_qss()
        self.resize(self.DEFAULT_SIZE)
        self.setMinimumSize(QSize(1000, 660))

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

        # Start on home screen
        self._show_home()

    def _apply_supplemental_qss(self) -> None:
        """Append extra QSS rules not in the base theme.

        Covers checkboxes, visible-on-dark-bg indicators, and any
        widget that the base STYLESHEET does not address.
        """
        from PyQt6.QtWidgets import QApplication
        from biopro.ui.theme import Colors
        extra = (
            # Checkbox — visible teal indicator on dark background
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

    # ── Menu Bar ──────────────────────────────────────────────────────

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()

        # File
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

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Analysis — actions now wired properly
        analysis_menu = menubar.addMenu("&Analysis")

        wb_action = QAction("&Western Blot Densitometry", self)
        wb_action.setShortcut("Ctrl+W")
        wb_action.setToolTip("Analyze western blot band densities")
        wb_action.triggered.connect(self._show_western_blot)
        analysis_menu.addAction(wb_action)

        # Help
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About BioPro", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── Central Widget ─────────────────────────────────────────────────

    def _setup_central_widget(self) -> None:
        """Root QStackedWidget: [0] Home  |  [1] Analysis."""
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

        # Contextual toolbar
        self.analysis_toolbar = AnalysisToolBar("Western Blot Analysis")
        self.analysis_toolbar.btn_home.clicked.connect(self._show_home)
        ap_layout.addWidget(self.analysis_toolbar)

        # Three-panel splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: wizard (fixed min/max width so it doesn't crowd the canvas)
        self.wizard_panel = WesternBlotPanel()
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.wizard_panel)
        left_container.setMinimumWidth(360)
        left_container.setMaximumWidth(560)

        # Centre: image canvas
        self.canvas = ImageCanvas()

        # Right: results — hidden until first results arrive
        self.results_widget = ResultsWidget()
        self._right_container = QWidget()
        right_layout = QVBoxLayout(self._right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.results_widget)
        self._right_container.setMinimumWidth(300)
        self._right_container.hide()

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(self._right_container)
        self.splitter.setSizes([420, 980, 0])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, True)

        ap_layout.addWidget(self.splitter, stretch=1)
        self.root_stack.addWidget(analysis_page)

        self.setCentralWidget(self.root_stack)

    # ── Status Bar ─────────────────────────────────────────────────────

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("subtitle")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")

    # ── Signal Wiring ──────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Home → analysis
        self.home_screen.western_blot_requested.connect(self._show_western_blot)

        # Give the wizard panel a direct canvas reference (for crop preview)
        self.wizard_panel.set_canvas(self.canvas)
        # Give the wizard panel a reference to the results widget so band
        # clicks can call highlight_band_for_comparison directly.
        self.wizard_panel.set_results_widget(self.results_widget)
        # Give results_widget a canvas ref so it can update A/B markers
        self.results_widget.set_canvas(self.canvas)

        # Wizard → Canvas
        self.wizard_panel.image_changed.connect(self.canvas.set_image)
        self.wizard_panel.lanes_detected.connect(
            lambda lanes: self.canvas.add_lane_overlays(lanes)
        )
        self.wizard_panel.bands_detected.connect(
            lambda bands, lanes: self.canvas.add_band_overlays(lanes, bands)
        )
        self.wizard_panel.peak_picking_enabled.connect(self.canvas.set_peak_picking_enabled)
        self.wizard_panel.crop_mode_toggled.connect(self.canvas.set_crop_mode)
        self.wizard_panel.profile_hovered.connect(self._on_profile_hovered)

        # Wizard → Results (also reveals the right panel on first result)
        self.wizard_panel.results_ready.connect(self._on_results_ready)
        self.wizard_panel.selected_bands_changed.connect(
            self.results_widget.update_pairwise_comparison
        )

        # Wizard → Status bar
        self.wizard_panel.status_message.connect(self.status_bar.showMessage)

        # Canvas → Wizard
        self.canvas.band_clicked.connect(self.wizard_panel.on_band_clicked)
        self.canvas.peak_pick_requested.connect(self.wizard_panel.on_peak_pick_requested)
        self.canvas.crop_requested.connect(self.wizard_panel.on_crop_requested)

        # Canvas zoom → status bar
        self.canvas.zoom_changed.connect(
            lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
        )

    # ── Navigation ─────────────────────────────────────────────────────

    def _show_home(self) -> None:
        # Reset the wizard panel so the user can change their setup options
        # (e.g. include/exclude Ponceau) when they re-enter the module.
        self.wizard_panel.reset_to_setup()
        self.root_stack.setCurrentIndex(_PAGE_HOME)
        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")
        self.zoom_label.setText("")

    def _show_western_blot(self) -> None:
        self.root_stack.setCurrentIndex(_PAGE_ANALYSIS)
        self.status_bar.showMessage(
            "Western Blot Analysis — open an image to begin  (Ctrl+O)"
        )

    # ── Results panel reveal ────────────────────────────────────────────

    def _on_results_ready(self, df) -> None:
        """Pass results to the widget and reveal the right panel if needed."""
        # Ensure the results widget ref is current (wizard may have been rebuilt)
        self.wizard_panel.set_results_widget(self.results_widget)
        self.results_widget.set_results(df)
        if self._right_container.isHidden():
            self._right_container.show()
            total = self.splitter.width()
            left = 340
            right = max(320, total // 4)
            centre = max(200, total - left - right)
            self.splitter.setSizes([left, centre, right])

    # ── Helpers ────────────────────────────────────────────────────────

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
        # Jump to analysis view first if we're on the home screen
        if self.root_stack.currentIndex() == _PAGE_HOME:
            self._show_western_blot()
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