"""Main application window for BioPro.

Assembles all UI components into a three-panel layout:

    ┌─────────────────────────────────────────────┐
    │                  Menu Bar                    │
    ├──────────┬────────────────────┬──────────────┤
    │          │                    │              │
    │  Wizard  │   Image Canvas     │   Results    │
    │  Panel   │   (zoom/pan)      │   (chart +   │
    │          │                    │    table)    │
    │          │                    │              │
    ├──────────┴────────────────────┴──────────────┤
    │                Status Bar                    │
    └─────────────────────────────────────────────┘

The wizard panel emits signals that update the canvas and results.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QLabel,
    QWidget,
    QVBoxLayout,
)

from biopro.ui.image_canvas import ImageCanvas
from biopro.ui.results_widget import ResultsWidget
from biopro.ui.western_blot_panel import WesternBlotPanel
from biopro.ui.theme import Colors

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """BioPro main application window.

    Provides:
        - Menu bar with File and Help menus.
        - Three-panel split layout: wizard | image | results.
        - Status bar for messages.
        - Signal wiring between wizard, canvas, and results.
    """

    APP_TITLE = "BioPro — Bio-Image Analysis"
    DEFAULT_SIZE = QSize(1400, 800)

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()

        self.setWindowTitle(self.APP_TITLE)
        self.resize(self.DEFAULT_SIZE)
        self.setMinimumSize(QSize(900, 600))

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._connect_signals()

    def _setup_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")

        wb_action = QAction("&Western Blot Densitometry", self)
        wb_action.setToolTip("Analyze western blot band densities")
        analysis_menu.addAction(wb_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About BioPro", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_central_widget(self) -> None:
        """Create the three-panel split layout."""
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: wizard
        self.wizard_panel = WesternBlotPanel()
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.wizard_panel)
        left_container.setMinimumWidth(320)

        # Center panel: image canvas
        self.canvas = ImageCanvas()

        # Right panel: results
        self.results_widget = ResultsWidget()
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.results_widget)
        right_container.setMinimumWidth(300)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(right_container)

        # Set initial proportions: 25% | 45% | 30%
        self.splitter.setSizes([320, 580, 400])

        self.setCentralWidget(self.splitter)

    def _setup_status_bar(self) -> None:
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Zoom indicator
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("subtitle")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.status_bar.showMessage("Welcome to BioPro — open an image to begin")

    def _connect_signals(self) -> None:
        """Wire signals between wizard, canvas, and results."""
        # Give the wizard panel a direct reference to the canvas so it can
        # call show_crop_preview() / clear_crop_preview() for the auto-crop flow.
        self.wizard_panel.set_canvas(self.canvas)

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

        # Wizard → Results
        self.wizard_panel.results_ready.connect(self.results_widget.set_results)
        self.wizard_panel.selected_bands_changed.connect(self.results_widget.update_pairwise_comparison)

        # Wizard → Status bar
        self.wizard_panel.status_message.connect(self.status_bar.showMessage)

        # Canvas interactions → Wizard
        self.canvas.band_clicked.connect(self.wizard_panel.on_band_clicked)
        self.canvas.peak_pick_requested.connect(self.wizard_panel.on_peak_pick_requested)
        self.canvas.crop_requested.connect(self.wizard_panel.on_crop_requested)

        # Canvas zoom → Status bar
        self.canvas.zoom_changed.connect(
            lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
        )

    def _on_profile_hovered(self, lane_idx: int, y_pos: float) -> None:
        """Highlight the corresponding position on the image when hovering a profile."""
        lanes = getattr(self.wizard_panel.analyzer.state, "lanes", [])
        if not lanes or lane_idx < 0 or lane_idx >= len(lanes):
            self.canvas.hide_hover_indicator()
            return

        # y_pos < 0 is used by the dialog to indicate "left axes"
        if y_pos < 0:
            self.canvas.hide_hover_indicator()
            return

        lane = lanes[lane_idx]
        y_image = lane.y_start + float(y_pos)
        self.canvas.show_hover_indicator(lane, y_image)

    def _on_open_file(self) -> None:
        """Handle File > Open menu action."""
        self.wizard_panel._open_file()

    def _show_about(self) -> None:
        """Show the About dialog."""
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