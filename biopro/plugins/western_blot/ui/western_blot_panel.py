"""Western Blot analysis panel.

Entry point for the Western Blot workflow.  Shows a setup screen first
so the user can choose optional stages (Ponceau normalization), then
builds a ``WizardPanel`` with the correct step list and switches to it.

This file is intentionally thin — all analysis logic lives in the step
classes under ``biopro/ui/wizard/steps/``.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from biopro.plugins.western_blot.analysis.western_blot import WesternBlotAnalyzer
from biopro.plugins.western_blot.analysis.ponceau import PonceauAnalyzer
from biopro.plugins.western_blot.ui.base import WizardPanel
from biopro.plugins.western_blot.ui.setup_screen import SetupScreen
from biopro.plugins.western_blot.ui.steps.wb_load import WBLoadStep
from biopro.plugins.western_blot.ui.steps.wb_lanes import WBLanesStep
from biopro.plugins.western_blot.ui.steps.wb_bands import WBBandsStep
from biopro.plugins.western_blot.ui.steps.wb_results import WBResultsStep
from biopro.plugins.western_blot.ui.steps.ponceau_load import PonceauLoadStep
from biopro.plugins.western_blot.ui.steps.ponceau_lanes import PonceauLanesStep
from biopro.plugins.western_blot.ui.steps.ponceau_bands import PonceauBandsStep

logger = logging.getLogger(__name__)

_PAGE_SETUP = 0
_PAGE_WIZARD = 1


class WesternBlotPanel(QWidget):
    """Western Blot entry point — setup screen then wizard.

    Exposes the same signals as the original monolithic panel so
    ``MainWindow`` needs no changes.
    """

    # ── Signals ───────────────────────────────────────────────────────
    status_message = pyqtSignal(str)
    image_changed = pyqtSignal(object)
    lanes_detected = pyqtSignal(object)
    bands_detected = pyqtSignal(object, object)
    results_ready = pyqtSignal(object)
    selected_bands_changed = pyqtSignal(list)
    peak_picking_enabled = pyqtSignal(bool)
    crop_mode_toggled = pyqtSignal(bool)
    profile_hovered = pyqtSignal(int, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._canvas = None
        self._wizard: WizardPanel | None = None
        self._wb_results_step: WBResultsStep | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # Page 0: setup screen
        self._setup_screen = SetupScreen()
        self._setup_screen.analysis_requested.connect(self._on_start_analysis)
        self._stack.addWidget(self._setup_screen)

        # Page 1: wizard — built dynamically on start
        self._wizard_placeholder = QWidget()
        self._stack.addWidget(self._wizard_placeholder)

        layout.addWidget(self._stack)

    # ── Public API ────────────────────────────────────────────────────

    def set_canvas(self, canvas) -> None:
        self._canvas = canvas
        if self._wizard is not None:
            self._wizard.set_canvas(canvas)

    def reset_to_setup(self) -> None:
        """Return to the setup screen and discard the current wizard.

        Called when the user navigates back to the home screen so they
        can change pipeline options (e.g. include/exclude Ponceau) on
        their next run.
        """
        if self._wizard is not None:
            self._stack.removeWidget(self._wizard)
            self._wizard.deleteLater()
            self._wizard = None
        self._wb_results_step = None

        self._wizard_placeholder = QWidget()
        self._stack.addWidget(self._wizard_placeholder)
        self._stack.setCurrentIndex(_PAGE_SETUP)

    # ── Slots forwarded from MainWindow / canvas ──────────────────────

    def on_band_clicked(self, band) -> None:
        if self._wizard:
            self._wizard.on_band_clicked(band)

    def on_peak_pick_requested(self, x: float, y: float) -> None:
        if self._wizard:
            self._wizard.on_peak_pick_requested(x, y)

    def on_crop_requested(self, rect) -> None:
        if self._wizard:
            self._wizard.on_crop_requested(rect)

    def set_results_widget(self, rw) -> None:
        """Pass the ResultsWidget reference so band clicks can update it directly.

        Also wires the slot-count spinner so changing the number of bands
        to compare triggers an automatic recompute.
        """
        if self._wizard is None:
            return

        self._wizard._results_widget_ref = rw

        # Wire slot-count spinner → recompute results automatically.
        # Disconnect any previous connection first to avoid duplicates.
        if rw is not None and self._wb_results_step is not None:
            try:
                rw._spin_slots.valueChanged.disconnect()
            except Exception:
                pass

            step = self._wb_results_step

            def _on_slots_changed(n: int) -> None:
                rw._rebuild_slots(n)
                step._compute_results()

            rw._spin_slots.valueChanged.connect(_on_slots_changed)

    @property
    def analyzer(self):
        """Expose WB analyzer so MainWindow._on_profile_hovered can read lanes."""
        if self._wizard is not None:
            return self._wizard.analyzer
        return WesternBlotAnalyzer()

    # ── Build and launch the wizard ───────────────────────────────────

    def _on_start_analysis(self, include_ponceau: bool) -> None:
        """Build step list from user choices and launch the wizard."""
        steps = []

        # ── Optional: Ponceau stage ───────────────────────────────────
        if include_ponceau:
            steps += [
                PonceauLoadStep(),
                PonceauLanesStep(),
                PonceauBandsStep(),
            ]

        # ── Western Blot stage ────────────────────────────────────────
        wb_load    = WBLoadStep()
        wb_lanes   = WBLanesStep()
        wb_bands   = WBBandsStep()
        wb_results = WBResultsStep()
        steps += [wb_load, wb_lanes, wb_bands, wb_results]

        # Store reference so set_results_widget can wire the spinner
        self._wb_results_step = wb_results

        # Wire lane detection → update ref lane combo in results step
        _orig_run = wb_lanes.run_detection
        def _run_and_update(panel):
            _orig_run(panel)
            wb_results.update_ref_lane_combo(len(panel.analyzer.state.lanes))
        wb_lanes.run_detection = _run_and_update

        # Build wizard
        wizard = WizardPanel(steps=steps, title="Western Blot Analysis")

        # Attach analyzers directly on the wizard instance so steps can
        # access them via panel.analyzer / panel.ponceau_analyzer
        wizard.analyzer = WesternBlotAnalyzer()
        wizard.ponceau_analyzer = PonceauAnalyzer() if include_ponceau else None

        # Filled by set_results_widget() once MainWindow passes the ref
        wizard._results_widget_ref = None

        # Forward all wizard signals → this panel's signals
        wizard.status_message.connect(self.status_message)
        wizard.image_changed.connect(self.image_changed)
        wizard.lanes_detected.connect(self.lanes_detected)
        wizard.bands_detected.connect(self.bands_detected)
        wizard.results_ready.connect(self.results_ready)
        wizard.selected_bands_changed.connect(self.selected_bands_changed)
        wizard.peak_picking_enabled.connect(self.peak_picking_enabled)
        wizard.crop_mode_toggled.connect(self.crop_mode_toggled)
        wizard.profile_hovered.connect(self.profile_hovered)

        if self._canvas is not None:
            wizard.set_canvas(self._canvas)

        # Replace placeholder and show wizard
        self._wizard = wizard
        self._stack.removeWidget(self._wizard_placeholder)
        self._stack.addWidget(wizard)
        self._stack.setCurrentWidget(wizard)