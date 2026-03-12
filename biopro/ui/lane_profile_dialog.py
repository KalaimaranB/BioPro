"""Dialog for viewing lane density profiles."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QCheckBox,
)

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

from biopro.analysis.western_blot import AnalysisState

# Use PyQt6 backend for matplotlib
matplotlib.use("QtAgg")


class LaneProfileDialog(QDialog):
    """A dialog to display the densitometry profile of lanes.
    
    Shows the raw density profile, estimated baseline, and detected peaks
    for the selected lane, making it easier to verify automated band detection
    and manually pick missed bands.
    
    Signals:
        profile_hovered(int, float): Emitted when mouse hovers over plot. Includes (lane_idx, y_pos).
        profile_clicked(int, float): Emitted when user clicks on plot. Includes (lane_idx, y_pos).
    """

    profile_hovered = pyqtSignal(int, float)
    profile_clicked = pyqtSignal(int, float)
    profile_range_selected = pyqtSignal(int, float, float)
    profile_band_removed = pyqtSignal(int, float)
    orientation_changed = pyqtSignal(int, bool)
    bands_updated = pyqtSignal()

    def __init__(self, state: AnalysisState, parent=None) -> None:
        """Initialize the dialog.
        
        Args:
            state: The current Western Blot AnalysisState.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Lane Profile Viewer")
        self.resize(900, 700)
        
        # Manual orientation override state
        self._force_valleys = None
        
        self._setup_ui()
        self._populate_lanes()
        self._update_plot()

    def _setup_ui(self) -> None:
        """Set up the dialog layout."""
        layout = QVBoxLayout(self)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("Select Lane:"))
        
        self.combo_lane = QComboBox()
        self.combo_lane.currentIndexChanged.connect(self._on_lane_changed)
        controls_layout.addWidget(self.combo_lane)
        
        controls_layout.addSpacing(20)
        
        self.check_flip = QCheckBox("Flip Peaks/Valleys")
        self.check_flip.setToolTip("Force bands to be treated as valleys instead of peaks (or vice versa)")
        self.check_flip.toggled.connect(self._on_flip_toggled)
        controls_layout.addWidget(self.check_flip)
        
        controls_layout.addStretch()
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        controls_layout.addWidget(self.btn_close)
        
        layout.addLayout(controls_layout)
        
        layout.addWidget(QLabel("<i>Drag on the plot to manually select a band region. Left-click to snap to peak. Right-click on a peak marker to remove.</i>"))

        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Connect Matplotlib events
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        # Mouse click still works for snapping and removal
        self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.canvas.mpl_connect("axes_leave_event", self._on_mouse_leave)

        # Implementation of SpanSelector for drag selection
        # We'll initialize it in _update_plot because it needs the axis
        self.span_selector = None

    def _on_mouse_move(self, event) -> None:
        """Handle mouse hover to trigger profile_hovered signal."""
        if getattr(self, "combo_lane", None) is None:
            return
            
        if event.inaxes:
            # event.xdata is the position in the lane
            idx = self.combo_lane.currentIndex()
            if idx >= 0:
                self.profile_hovered.emit(idx, float(event.xdata))
        else:
            self._on_mouse_leave(event)

    def _on_mouse_leave(self, event) -> None:
        """Handle mouse leaving the axes to clear the hover indicator."""
        if getattr(self, "combo_lane", None) is None:
            return
            
        idx = self.combo_lane.currentIndex()
        if idx >= 0:
            # Emit -1 to indicate leaving
            self.profile_hovered.emit(idx, -1.0)

    def _on_mouse_click(self, event) -> None:
        """Handle mouse click and emit profile_clicked or profile_band_removed signal."""
        if not event.inaxes:
            return
            
        idx = self.combo_lane.currentIndex()
        if idx < 0:
            return

        # Left click: Add/Snap band
        if event.button == 1:
            self.profile_clicked.emit(idx, float(event.xdata))
        # Right click: Remove band
        elif event.button == 3:
            self.profile_band_removed.emit(idx, float(event.xdata))

    def _on_flip_toggled(self, checked: bool) -> None:
        """Handle profile orientation flip."""
        idx = self.combo_lane.currentIndex()
        if idx < 0:
            return
            
        self._force_valleys = checked
        self.orientation_changed.emit(idx, checked)

    def _on_lane_changed(self, idx: int) -> None:
        """Update UI state when a different lane is selected."""
        if idx < 0:
            return
            
        # Update flip checkbox state from analyzer state
        if hasattr(self.state, "lane_orientations") and idx < len(self.state.lane_orientations):
            self.check_flip.blockSignals(True)
            self.check_flip.setChecked(self.state.lane_orientations[idx])
            self.check_flip.blockSignals(False)
            self._force_valleys = self.state.lane_orientations[idx]
        else:
            self.check_flip.blockSignals(True)
            self.check_flip.setChecked(False)
            self.check_flip.blockSignals(False)
            self._force_valleys = False
            
        self._update_plot()

    def _populate_lanes(self) -> None:
        """Populate the lane selector."""
        self.combo_lane.clear()
        if not self.state.lanes:
            self.combo_lane.addItem("No lanes detected")
            self.combo_lane.setEnabled(False)
            return

        self.combo_lane.setEnabled(True)
        for i in range(len(self.state.lanes)):
            self.combo_lane.addItem(f"Lane {i + 1}")

    def _update_plot(self) -> None:
        """Redraw the plot for the selected lane."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        idx = self.combo_lane.currentIndex()
        
        if not self.state.profiles or idx < 0 or idx >= len(self.state.profiles):
            ax.text(0.5, 0.5, "No profile data available.\nRun 'Detect Bands' first.", 
                    ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
            
        profile = self.state.profiles[idx]
        baseline = self.state.baselines[idx] if self.state.baselines else None
        
        # Plot profile
        x = np.arange(len(profile))
        ax.plot(x, profile, label="Raw Density", color="#2c3e50", linewidth=1.5)
        
        # Plot baseline if available
        if baseline is not None:
            ax.plot(x, baseline, label="Estimated Baseline", color="#e74c3c", linestyle="--", linewidth=1.5)
            # Shade area under the curve
            ax.fill_between(x, baseline, profile, where=(profile > baseline), 
                            color="#3498db", alpha=0.3, label="Band Area")
                            
        # Plot detected bands for this lane
        lane_bands = [b for b in self.state.bands if b.lane_index == idx]
        for b in lane_bands:
            # Mark the peak position
            y_val = profile[int(b.position)] if 0 <= int(b.position) < len(profile) else b.raw_height
            ax.plot(b.position, y_val, marker="v", color="#f39c12", markersize=8)
            
            # Show approximate integration bounds based on width
            if b.width > 0:
                half_w = b.width / 2.0
                left = max(0, b.position - half_w)
                right = min(len(profile) - 1, b.position + half_w)
                ax.axvspan(left, right, color="#f1c40f", alpha=0.2)
                
        ax.set_title(f"Density Profile - Lane {idx + 1}")
        ax.set_xlabel("Vertical Position (pixels)")
        ax.set_ylabel("Intensity")
        
        # Invert x-axis so it matches the top-to-bottom image convention
        # (Pixel 0 is at the top of the image)
        ax.set_xlim(len(profile) - 1, 0)
        
        ax.grid(True, linestyle=":", alpha=0.6)
        if baseline is not None or lane_bands:
            ax.legend()
            
        # Re-initialize SpanSelector
        self.span_selector = SpanSelector(
            ax,
            self._on_span_select,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.3, facecolor="#f1c40f"),
            interactive=True,
            drag_from_anywhere=True,
        )
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def _on_span_select(self, xmin, xmax):
        """Handle range selection via SpanSelector."""
        idx = self.combo_lane.currentIndex()
        if idx < 0:
            return
            
        # Only proceed if range is meaningful
        if abs(xmax - xmin) < 2:
            return
            
        self.profile_range_selected.emit(idx, float(xmin), float(xmax))
