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
        
        self.check_flip = QCheckBox("Invert (bands are bright peaks)")
        self.check_flip.setToolTip(
            "By default bands are detected as dark valleys (standard dark-on-white blot).\n"
            "Check this if your bands are bright on a dark background (e.g. fluorescent)."
        )
        self.check_flip.toggled.connect(self._on_flip_toggled)
        controls_layout.addWidget(self.check_flip)
        
        controls_layout.addStretch()
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        controls_layout.addWidget(self.btn_close)
        
        layout.addLayout(controls_layout)

        # Fix #4: Use a proper wrapping label for the hint
        hint_lbl = QLabel("Drag on the plot to manually add a band region. Left-click to snap to nearest peak. Right-click on a marker to remove it.")
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color: #8b949e; font-style: italic; padding: 2px 0;")
        layout.addWidget(hint_lbl)

        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Track whether the NavigationToolbar is in a zoom/pan mode so we
        # can disable span-selection while the user is panning/zooming.
        self._nav_mode_active = False
        # Watch toolbar mode changes so SpanSelector is suppressed during pan/zoom
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("axes_leave_event", self._on_mouse_leave)
        # Fix #3: Use button_release instead of button_press so the SpanSelector
        # drag completes before we decide whether it was a click vs drag.
        self.canvas.mpl_connect("button_release_event", self._on_mouse_release)

        # SpanSelector is initialised in _update_plot (needs axes reference)
        self.span_selector = None
        self._drag_active = False   # True while user is dragging a span

    def _on_mouse_move(self, event) -> None:
        """Handle mouse hover to trigger profile_hovered signal."""
        if getattr(self, "combo_lane", None) is None:
            return

        # Mark that the user is dragging if a button is held down
        if event.button is not None and event.button != 0:
            self._drag_active = True

        if event.inaxes:
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
            self.profile_hovered.emit(idx, -1.0)

    def _on_mouse_release(self, event) -> None:
        """Handle mouse release — emit click only if not a drag operation.
        
        Fix #3: Using release instead of press so the SpanSelector finishes
        its drag before we decide whether to treat the action as a point-click.
        """
        if not event.inaxes:
            self._drag_active = False
            return

        idx = self.combo_lane.currentIndex()
        if idx < 0:
            self._drag_active = False
            return

        # If a span drag was in progress, let SpanSelector handle it; don't
        # also fire a point-click.
        if self._drag_active:
            self._drag_active = False
            return

        # Left click: snap to nearest peak
        if event.button == 1:
            # Suppress click while toolbar pan/zoom is active
            try:
                mode = self.toolbar.mode
                if hasattr(mode, 'name'):
                    mode = mode.name
                if str(mode) not in ("", "NONE"):
                    return
            except Exception:
                pass
            self.profile_clicked.emit(idx, float(event.xdata))
        # Right click: remove band near cursor
        elif event.button == 3:
            self.profile_band_removed.emit(idx, float(event.xdata))

    def _on_flip_toggled(self, checked: bool) -> None:
        """Handle profile orientation flip.
        
        Unchecked (default) = dark valleys are bands (dark-on-white blot).
        Checked = bright peaks are bands (fluorescent / inverted blot).
        """
        idx = self.combo_lane.currentIndex()
        if idx < 0:
            return
        # checked=True means user says bands are peaks → force_valleys_as_bands=False
        force_valleys = not checked
        self._force_valleys = force_valleys
        self.orientation_changed.emit(idx, force_valleys)

    def _on_lane_changed(self, idx: int) -> None:
        """Update UI state when a different lane is selected."""
        if idx < 0:
            return
            
        # Update flip checkbox: unchecked = valleys (default dark-on-white),
        # checked = peaks (fluorescent/inverted).
        if hasattr(self.state, "lane_orientations") and idx < len(self.state.lane_orientations):
            valleys_as_bands = bool(self.state.lane_orientations[idx])
            self.check_flip.blockSignals(True)
            self.check_flip.setChecked(not valleys_as_bands)  # checked means peaks mode
            self.check_flip.blockSignals(False)
            self._force_valleys = valleys_as_bands
        else:
            self.check_flip.blockSignals(True)
            self.check_flip.setChecked(False)  # unchecked = valleys (default)
            self.check_flip.blockSignals(False)
            self._force_valleys = True
            
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

        # state.profiles already stores the oriented display_profile from
        # analyze_lane — bands are always positive peaks regardless of
        # original image polarity. Plot it directly, no re-flipping needed.
        display_profile = np.asarray(self.state.profiles[idx], dtype=np.float64)
        baseline = np.asarray(self.state.baselines[idx], dtype=np.float64) if self.state.baselines else None

        valleys_as_bands = False
        if hasattr(self.state, "lane_orientations") and idx < len(self.state.lane_orientations):
            valleys_as_bands = bool(self.state.lane_orientations[idx])

        x = np.arange(len(display_profile))
        ax.plot(x, display_profile, label="Density Profile", color="#2c3e50", linewidth=1.5)
        
        if baseline is not None:
            ax.plot(x, baseline, label="Estimated Baseline", color="#e74c3c", linestyle="--", linewidth=1.5)
            ax.fill_between(x, baseline, display_profile,
                            where=(display_profile > baseline),
                            color="#3498db", alpha=0.3, label="Band Area")
                            
        # Band markers — positions are in display_profile space (bands=peaks)
        lane_bands = [b for b in self.state.bands if b.lane_index == idx]
        for b in lane_bands:
            pos = int(b.position)
            y_val = display_profile[pos] if 0 <= pos < len(display_profile) else b.raw_height
            ax.plot(pos, y_val, marker="^", color="#f39c12", markersize=9,
                    zorder=5, markeredgecolor="#c0392b", markeredgewidth=0.8)
            if b.width > 0:
                half_w = b.width / 2.0
                left = max(0, b.position - half_w)
                right = min(len(display_profile) - 1, b.position + half_w)
                ax.axvspan(left, right, color="#f1c40f", alpha=0.2)
                
        title_suffix = " [Flipped — valleys treated as bands]" if valleys_as_bands else ""
        ax.set_title(f"Density Profile — Lane {idx + 1}{title_suffix}")
        ax.set_xlabel("Vertical Position (pixels)")
        ax.set_ylabel("Intensity")
        
        # Pixel 0 is at the top of the gel image
        ax.set_xlim(len(display_profile) - 1, 0)
        
        ax.grid(True, linestyle=":", alpha=0.6)
        if baseline is not None or lane_bands:
            ax.legend(fontsize=8)
            
        self.span_selector = SpanSelector(
            ax,
            self._on_span_select,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.3, facecolor="#f1c40f"),
            interactive=False,
            drag_from_anywhere=False,
        )
        self._drag_active = False
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def _on_span_select(self, xmin, xmax):
        """Handle range selection via SpanSelector.
        
        Fix #3: The x-axis is inverted (decreasing left-to-right) so xmin/xmax
        from SpanSelector may be swapped relative to pixel coordinates.
        Always normalize so start <= end in pixel space.
        """
        # Mark this event as a drag so the button_release handler won't also
        # fire a point-click for the same mouse action.
        self._drag_active = True

        idx = self.combo_lane.currentIndex()
        if idx < 0:
            return
            
        # Normalize — pixel coords must be ascending
        lo, hi = min(xmin, xmax), max(xmin, xmax)

        # Only proceed if range is meaningful (at least 3 pixels wide)
        if hi - lo < 3:
            return
            
        self.profile_range_selected.emit(idx, float(lo), float(hi))