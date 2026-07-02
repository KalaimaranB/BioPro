"""Workspace Window for BioPro."""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QSize,
    Qt,
    QThread,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from biopro.core.config import AppConfig
from biopro.core.event_bus import BioProEvent, event_bus
from biopro.ui.components.ai_panel import AIChatWindow
from biopro.ui.components.toolbars import AnalysisToolBar
from biopro.ui.dashboards.workspace_dashboard import WorkspaceDashboard as HomeScreen
from biopro.ui.theme import Colors, Fonts, theme_manager
from biopro.ui.widgets.galactic_loader import GalacticLoader

logger = logging.getLogger(__name__)
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)

_PAGE_HOME = 0
_PAGE_ANALYSIS = 1
_PAGE_LOADING = 2


class PluginUIWorker(QObject):
    """Worker to handle the slow import of plugin modules off the main thread."""

    finished = pyqtSignal(object)  # Passes the PanelClass
    error = pyqtSignal(str)

    def __init__(self, module_manager, module_id, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.module_id = module_id

    @pyqtSlot()
    def run(self):
        try:
            # This is the 'Rainbow Wheel' culprit (the imports inside load_module_ui)
            PanelClass = self.module_manager.load_module_ui(self.module_id)
            self.finished.emit(PanelClass)
        except Exception:
            import traceback

            self.error.emit(traceback.format_exc())


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

        from biopro.ui.theme import Strings

        project_name = self.project_manager.data.get("project_name", "Untitled Project")
        self.setWindowTitle(f"{Strings.APP_TITLE} — {project_name}")
        self.setMinimumSize(1200, 800)

        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")

        self._apply_supplemental_qss()

        # Restore window geometry from preferences
        from PyQt6.QtCore import QByteArray

        from biopro.core.preferences import core_preferences

        saved_geom = core_preferences.get("workspace_window_geometry")
        if saved_geom:
            self.restoreGeometry(QByteArray.fromHex(saved_geom.encode("ascii")))
        else:
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

        self._ai_window = None
        self._module_thread = None
        self._module_worker = None
        self._pending_workflow_payload: dict | None = None
        self._pending_manifest: dict | None = None
        self._pending_panel_class: type | None = None

        self._show_home()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    @staticmethod
    def _write_checkbox_svgs() -> tuple[str, str]:
        """Write theme-aware SVG checkbox images to a temp dir and return their paths."""
        import os
        import tempfile

        # Checked — accent-filled box with white checkmark polyline
        checked_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            f'<rect width="16" height="16" rx="3" fill="{Colors.ACCENT_PRIMARY}"/>'
            '<polyline points="3,8.5 6.5,12 13,4" fill="none" stroke="white"'
            ' stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
            "</svg>"
        )
        # Unchecked — neutral box, clearly bordered
        unchecked_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
            f'<rect x="1" y="1" width="14" height="14" rx="3"'
            f' fill="{Colors.BG_MEDIUM}" stroke="{Colors.FG_SECONDARY}" stroke-width="1.5"/>'
            "</svg>"
        )

        tmp = tempfile.gettempdir()
        checked_path = os.path.join(tmp, "biopro_cb_checked.svg")
        unchecked_path = os.path.join(tmp, "biopro_cb_unchecked.svg")

        with open(checked_path, "w", encoding="utf-8") as f:
            f.write(checked_svg)
        with open(unchecked_path, "w", encoding="utf-8") as f:
            f.write(unchecked_svg)

        return checked_path, unchecked_path

    def _apply_supplemental_qss(self) -> None:
        checked_path, unchecked_path = self._write_checkbox_svgs()

        extra = (
            f"QCheckBox {{ spacing: 8px; color: {Colors.FG_PRIMARY}; }}"
            # ── Standalone QCheckBox indicators ──────────────────────────────
            f"QCheckBox::indicator {{ width: 16px; height: 16px; }}"
            f"QCheckBox::indicator:unchecked {{ image: url({unchecked_path}); }}"
            f"QCheckBox::indicator:checked   {{ image: url({checked_path}); }}"
            # ── QListWidget item checkboxes (ItemIsUserCheckable) ─────────────
            # These use QListView::indicator, which is a separate selector.
            f"QListView::indicator {{ width: 16px; height: 16px; }}"
            f"QListView::indicator:unchecked {{ image: url({unchecked_path}); }}"
            f"QListView::indicator:checked   {{ image: url({checked_path}); }}"
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
        if isinstance(app, QApplication):
            app.setStyleSheet("")
            app.setStyleSheet(extra)

    def _setup_menu_bar(self) -> None:
        menubar = self.menuBar()
        assert menubar is not None

        file_menu = QMenu("&File", self)
        menubar.addMenu(file_menu)

        # --- Edit Menu for History ---
        edit_menu = QMenu("&Edit", self)
        menubar.addMenu(edit_menu)

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

        open_action = QAction("&Open File...", self)
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

        theme_menu = QMenu("&Theme", self)
        menubar.addMenu(theme_menu)

        # DYNAMIC THEME DISCOVERY
        available_themes = theme_manager.discover_themes()
        for name, path in available_themes:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, p=path: self._switch_theme(p))
            theme_menu.addAction(action)

        # Help Menu
        help_menu = QMenu("&Help", self)
        menubar.addMenu(help_menu)

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
        self.analysis_page = QWidget()
        self.analysis_page.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        ap_layout = QVBoxLayout(self.analysis_page)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.setSpacing(0)

        self.analysis_toolbar = AnalysisToolBar("Analysis")
        self.analysis_toolbar.btn_home.clicked.connect(self._show_home)
        self.analysis_toolbar.btn_close_project.clicked.connect(self.return_to_hub)
        self.analysis_toolbar.btn_ai.clicked.connect(self._open_ai_chat)
        self.analysis_toolbar.btn_academy.clicked.connect(self._open_academy)

        # --- NEW: Aurebesh/Techy Subtitle ---
        self.aurebesh_lbl = QLabel("")
        self.aurebesh_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.aurebesh_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; font-size: 9px; padding-bottom: 2px; background: {Colors.BG_DARK}; border-bottom: 1px solid {Colors.BORDER};"
        )

        ap_layout.addWidget(self.analysis_toolbar)
        ap_layout.addWidget(self.aurebesh_lbl)

        self.wizard_panel = None
        self.main_module_container = QWidget()
        self.main_module_layout = QVBoxLayout(self.main_module_container)
        self.main_module_layout.setContentsMargins(0, 0, 0, 0)

        ap_layout.addWidget(self.main_module_container, stretch=1)

        # --- NEW: Hologram Effect Overlay ---
        from biopro.ui.effects.hologram_effect import HologramEffect

        self.hologram_overlay = HologramEffect(self.analysis_page)
        self.hologram_overlay.hide()  # Hidden by default, shown via theme

        self.root_stack.addWidget(self.analysis_page)

        # --- NEW: Tutorial Overlay ---
        from biopro.ui.wizards.tutorial_overlay import TutorialOverlay

        self.tutorial_overlay = TutorialOverlay(self.analysis_page)
        self.tutorial_overlay.hide()

        # We hook into global manager
        self.tutorial_overlay.btn_next.clicked.connect(self._on_tutorial_next)
        self.tutorial_overlay.btn_close.clicked.connect(self._on_tutorial_skip)
        self._tutorial_connections: dict = {}
        self._tutorial_last_step_id: str | None = None
        self._verification_wait: int = 0
        self.startTimer(100)  # Polling for overlay sync

        # ── Page 2: Loading Screen (Galactic Hyperspace) ─────────────
        self.loading_screen = GalacticLoader()
        self.root_stack.addWidget(self.loading_screen)

        self.setCentralWidget(self.root_stack)

    def _on_tutorial_next(self) -> None:
        """Called when the overlay Next button is clicked.

        For VerificationStep with allow_interaction=True the 'Next' button
        is labelled 'Check ✓'; clicking it runs the validator immediately
        rather than waiting for the background timer.
        """
        from biopro.core.models.tutorial_models import VerificationStep
        from biopro.core.tutorial_manager import global_tutorial_manager

        step = global_tutorial_manager.current_step
        if (
            step
            and isinstance(step, VerificationStep)
            and getattr(step, "allow_interaction", False)
        ):
            app_state = getattr(getattr(self, "wizard_panel", None), "state", None)
            if step.validator and step.validator.validate(app_state):
                global_tutorial_manager.next_step(step.on_success_step_id)
            elif step.on_fail_step_id:
                global_tutorial_manager.next_step(step.on_fail_step_id)
        else:
            global_tutorial_manager.next_step()

    def _on_tutorial_skip(self) -> None:
        """Hide the overlay and stop the active course."""
        from biopro.core.tutorial_manager import global_tutorial_manager

        self.tutorial_overlay.hide()
        global_tutorial_manager.active_course = None
        global_tutorial_manager.current_step = None

        wizard_panel = getattr(self, "wizard_panel", None)
        if wizard_panel:
            for canvas in wizard_panel.findChildren(QWidget, "FlowCanvas"):
                if hasattr(canvas, "set_guide_polygon"):
                    canvas.set_guide_polygon(None)

    def timerEvent(self, event) -> None:
        super().timerEvent(event)
        if not hasattr(self, "tutorial_overlay") or not self.tutorial_overlay.isVisible():
            return

        from biopro.core.models.tutorial_models import InteractionStep, VerificationStep
        from biopro.core.tutorial_manager import global_tutorial_manager

        step = global_tutorial_manager.current_step
        if not step:
            self.tutorial_overlay.hide()
            return

        # Only update geometry and raise if the rect changed to prevent rendering glitches
        new_geom = self.analysis_page.rect()
        if self.tutorial_overlay.geometry() != new_geom:
            self.tutorial_overlay.setGeometry(new_geom)
            self.tutorial_overlay.raise_()

        # Re-render the bubble if the step changed
        current_id = step.id
        if current_id != self._tutorial_last_step_id:
            self._tutorial_last_step_id = current_id
            self._verification_wait = 0
            self.tutorial_overlay.raise_()
            self.tutorial_overlay.render_step(step)

            guide_poly = getattr(step, "guide_poly", None)
            wizard_panel = getattr(self, "wizard_panel", None)
            if wizard_panel:
                for canvas in wizard_panel.findChildren(QWidget, "FlowCanvas"):
                    if hasattr(canvas, "set_guide_polygon"):
                        canvas.set_guide_polygon(guide_poly)

            # Wire InteractionStep signal → auto-advance
            if isinstance(step, InteractionStep) and step.target_widget_name:
                wizard_panel = getattr(self, "wizard_panel", None)
                if wizard_panel:
                    targets = wizard_panel.findChildren(QWidget, step.target_widget_name)
                    for target_w in targets:
                        if hasattr(target_w, step.event_trigger):
                            obj_id = id(target_w)
                            conn_key = f"{step.id}__{step.target_widget_name}__{step.event_trigger}__{obj_id}"
                            if conn_key not in self._tutorial_connections:
                                print(f"DEBUG: Wiring InteractionStep signal {conn_key}")

                                def _make_advancer(sid: str):
                                    def _advance(*_args):
                                        print(
                                            f"DEBUG: InteractionStep trigger fired for {sid}! current step is {global_tutorial_manager.current_step.id if global_tutorial_manager.current_step else None}"
                                        )
                                        if (
                                            global_tutorial_manager.current_step
                                            and global_tutorial_manager.current_step.id == sid
                                        ):
                                            print("DEBUG: Advancing next_step!")
                                            global_tutorial_manager.next_step()

                                    return _advance

                                advancer = _make_advancer(step.id)
                                self._tutorial_connections[conn_key] = advancer
                                try:
                                    getattr(target_w, step.event_trigger).connect(advancer)
                                    print(
                                        f"DEBUG: Successfully connected to {step.event_trigger} on widget {obj_id}"
                                    )
                                except Exception as e:
                                    print(
                                        f"DEBUG: Failed to connect to {step.event_trigger} on widget {obj_id}: {e}"
                                    )

        # Auto-verify VerificationStep
        if isinstance(step, VerificationStep) and step.validator:
            self._verification_wait += 1
            if self._verification_wait > 20:  # ~2 s at 100 ms ticks
                self._verification_wait = 0
                app_state = getattr(getattr(self, "wizard_panel", None), "state", None)

                try:
                    is_valid = step.validator.validate(app_state)
                    print(f"DEBUG: Validation result for {step.id}: {is_valid}")
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    print(f"DEBUG: Validation error: {e}")
                    is_valid = False

                if is_valid:
                    global_tutorial_manager.next_step(step.on_success_step_id)
                elif not getattr(step, "allow_interaction", False) and step.on_fail_step_id:
                    global_tutorial_manager.next_step(step.on_fail_step_id)

        # Auto-execute ActionStep
        if step.__class__.__name__ == "ActionStep" and step.id != getattr(
            self, "_last_action_step_executed", None
        ):
            self._last_action_step_executed = step.id
            try:
                wizard_panel = getattr(self, "wizard_panel", None)
                if step.action and wizard_panel:
                    step.action(wizard_panel)
            except Exception as e:
                import traceback

                traceback.print_exc()
                print(f"DEBUG: ActionStep error: {e}")
            global_tutorial_manager.next_step(step.next_step_id)

        # Spotlight: find target widgets and map to overlay-local coordinates
        targets: list[QWidget] = []
        wizard_panel = getattr(self, "wizard_panel", None)
        if wizard_panel:
            for attr in ("target_widget_name",):
                name = getattr(step, attr, "")
                if name:
                    w = wizard_panel.findChild(QWidget, name)
                    if w and w.isVisible():
                        targets.append(w)
            for name in getattr(step, "target_widget_names", []):
                for w in wizard_panel.findChildren(QWidget, name):
                    if w and w.isVisible():
                        targets.append(w)

        from PyQt6.QtCore import QRect

        rects = []
        for w in targets:
            global_pos = w.mapToGlobal(w.rect().topLeft())
            local_pos = self.tutorial_overlay.mapFromGlobal(global_pos)
            rects.append(QRect(local_pos, w.size()))
        self.tutorial_overlay.set_targets(rects)

    def _open_academy(self):
        from biopro.core.tutorial_manager import global_tutorial_manager
        from biopro.ui.dialogs.academy_window import AcademyWindow

        mod_id = getattr(self, "current_module_id", None)
        if not mod_id:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                self, "Academy", "Please load a module first to access its Academy."
            )
            return

        dialog = AcademyWindow(global_tutorial_manager, mod_id, self)
        dialog.exec()

        if global_tutorial_manager.active_course:
            self.tutorial_overlay.setGeometry(self.analysis_page.rect())
            self.tutorial_overlay.show()
            self.status_bar.showMessage(
                "Started Academy Course: " + global_tutorial_manager.active_course.title
            )

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        is_sw = "Galactic" in theme_manager.current_theme_name
        self.status_bar.setStyleSheet(
            f"background: {Colors.BG_DARK}; color: {Colors.FG_SECONDARY};"
            f" border-top: 1px solid {Colors.BORDER};"
            f" font-family: {Fonts.FAMILY_MONO if is_sw else 'inherit'};"
        )

        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("subtitle")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")

    def _connect_signals(self) -> None:
        self.home_screen.module_selected.connect(self._open_module)
        self.home_screen.return_to_hub_requested.connect(self.return_to_hub)
        self.home_screen.open_store_requested.connect(self._open_store)
        self.home_screen.open_ai_requested.connect(self._open_ai_chat)

        # ── THE NEW WORKFLOW SIGNALS ──
        self.home_screen.workflow_selected.connect(self._load_workflow_from_dashboard)
        self.home_screen.workflow_settings_requested.connect(self._handle_workflow_settings)
        self.home_screen.trust_module_requested.connect(self._on_trust_requested)
        self.home_screen.open_academy_requested.connect(self._open_academy_from_home)

    def _open_academy_from_home(self):
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "BioPro Academy",
            "Academy courses are module-specific. Please open an analysis module first to access its Academy.",
        )

    def _show_home(self) -> None:
        if self.wizard_panel and hasattr(self.wizard_panel, "reset_to_setup"):
            self.wizard_panel.reset_to_setup()

        self.current_module_id = None
        self._transition_to_page(_PAGE_HOME)

        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")
        self.zoom_label.setText("")

    def _open_module(self, manifest: dict) -> None:
        """Triggers the Galactic transition and starts async module loading."""
        module_id = manifest["id"]
        module_name = manifest.get("name", "Analysis Module")

        # 1. Setup the Loading Screen
        self.loading_screen.set_module(module_name)
        self._transition_to_page(_PAGE_LOADING)

        # 2. Cleanup existing thread if any
        if self._module_thread and self._module_thread.isRunning():
            self._module_thread.quit()
            self._module_thread.wait()

        # 3. Kick off the background worker
        self._module_thread = QThread(self)
        self._module_worker = PluginUIWorker(self.module_manager, module_id)
        self._module_worker.moveToThread(self._module_thread)

        self._module_thread.started.connect(self._module_worker.run)
        self._module_worker.finished.connect(
            lambda PanelClass: self._on_module_loaded(manifest, PanelClass)
        )
        self._module_worker.error.connect(lambda err: self._on_module_load_error(module_id, err))

        # Cleanup when done
        self._module_worker.finished.connect(self._module_thread.quit)
        self._module_worker.error.connect(self._module_thread.quit)

        self._module_thread.start()

    def _on_module_loaded(self, manifest: dict, PanelClass: type) -> None:
        """Callback for when the background thread finished importing the module.

        Transition design
        -----------------
        1. ``warp_out()`` fires IMMEDIATELY — the animation transitions to "ARRIVING AT
           DESTINATION" right away while the event loop is still free.
        2. When the warp peaks (``warp_out_finished``), build the plugin panel on the
           main thread.  The unavoidable construction freeze happens AFTER the cinematic
           warp-out, not before it — so "travelling" is the longest phase and "arriving"
           is a brief, dramatic flash.
        3. Panel ready → ``_crossfade_to_analysis()`` reveals the UI.
        """
        module_id = manifest["id"]
        self.current_module_id = module_id
        self._pending_manifest = manifest
        self._pending_panel_class = PanelClass

        # Step 1: Start warp-out immediately — animation keeps running uninterrupted
        with contextlib.suppress(TypeError):
            self.loading_screen.warp_out_finished.disconnect()

        self.loading_screen.warp_out_finished.connect(self._on_warp_peaked)
        self.loading_screen.warp_out()

    def _on_warp_peaked(self) -> None:
        """Called when the warp-out animation reaches its visual peak.

        The panel is built here (synchronously, on the main thread).  Any freeze
        during construction is now sandwiched between the "ARRIVING" flash and the
        crossfade — the travelling hyperspace phase is never interrupted.
        """
        with contextlib.suppress(TypeError):
            self.loading_screen.warp_out_finished.disconnect(self._on_warp_peaked)

        manifest = self._pending_manifest
        PanelClass = self._pending_panel_class
        self._pending_manifest = None
        self._pending_panel_class = None

        self._instantiate_module_panel(manifest, PanelClass)
        self._crossfade_to_analysis()

    def _instantiate_module_panel(self, manifest: dict, PanelClass: type) -> None:
        """Construct the plugin widget on the main thread.

        Called BEFORE any transition animation so the widget is ready to be
        revealed by the crossfade — never blocks the visible animation.
        """
        module_id = manifest["id"]
        try:
            if self.wizard_panel is not None:
                if hasattr(self.wizard_panel, "cleanup"):
                    self.wizard_panel.cleanup()
                self.wizard_panel.setParent(None)
                self.wizard_panel.deleteLater()

            self.wizard_panel = PanelClass()
            assert self.wizard_panel is not None
            self.wizard_panel.project_manager = self.project_manager

            self.main_module_layout.addWidget(self.wizard_panel)

            if hasattr(self.wizard_panel, "canvas") and hasattr(
                self.wizard_panel.canvas, "zoom_changed"
            ):
                self.wizard_panel.canvas.zoom_changed.connect(
                    lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
                )
            elif hasattr(self.wizard_panel, "zoom_changed"):
                self.wizard_panel.zoom_changed.connect(
                    lambda z: self.zoom_label.setText(f"{z * 100:.0f}%")
                )

            self.analysis_toolbar.set_title(
                manifest.get("icon", "📦"), manifest.get("name", "Analysis")
            )

            if "Galactic" in theme_manager.current_theme_name:
                self.aurebesh_lbl.setText(
                    f"PROJECT: {self.project_manager.data.get('project_name', 'UNKNOWN')} | NODE: {module_id.upper()} | ENCRYPTION: ACTIVE"
                )
                self.aurebesh_lbl.show()
            else:
                self.aurebesh_lbl.hide()

            if hasattr(self.wizard_panel, "status_message"):
                self.wizard_panel.status_message.connect(self.status_bar.showMessage)
            if hasattr(self.wizard_panel, "state_changed"):
                self.wizard_panel.state_changed.connect(self._push_history)

            # Inject any pending workflow payload
            if (
                hasattr(self, "_pending_workflow_payload")
                and self._pending_workflow_payload is not None
            ):
                if hasattr(self.wizard_panel, "load_workflow"):
                    import inspect

                    sig = inspect.signature(self.wizard_panel.load_workflow)
                    kwargs = {}
                    if "filename" in sig.parameters:
                        kwargs["filename"] = getattr(self, "_pending_workflow_filename", None)
                    if "metadata" in sig.parameters:
                        kwargs["metadata"] = getattr(self, "_pending_workflow_metadata", None)

                    self.wizard_panel.load_workflow(self._pending_workflow_payload, **kwargs)
                    self.status_bar.showMessage("Successfully loaded workflow payload.")
                self._pending_workflow_payload = None
                self._pending_workflow_filename = None
                self._pending_workflow_metadata = None

            self.status_bar.showMessage(f"{manifest.get('name')} — open a file to begin (Ctrl+O)")

        except Exception:
            import traceback

            self._on_module_load_error(module_id, traceback.format_exc())

    def _crossfade_to_analysis(self) -> None:
        """Crossfade from the running loader directly into the analysis page.

        ``QStackedWidget`` only paints the *current* widget, so we can't simply
        make the analysis page transparent to see the loader behind it.  Instead
        we flip the approach:

        1. Switch the stack to the analysis page (fully rendered, no effect).
        2. Reparent the loader as a **floating overlay** child of ``root_stack``
           covering its full geometry.
        3. Attach a ``QGraphicsOpacityEffect`` to the *loader overlay* and
           animate it from 1.0 → 0.0 over ~350 ms.
        4. When done, re-add the loader back into the stack and stop its timer.

        The result: the analysis page is fully visible underneath while the
        hyperspace dissolves out on top — continuous animation, zero black frame.
        """
        # Guard: don't double-fire
        with contextlib.suppress(TypeError):
            self.loading_screen.warp_out_finished.disconnect(self._crossfade_to_analysis)

        # 1. Remove the loader from the QStackedWidget so it becomes a free widget
        self.root_stack.removeWidget(self.loading_screen)

        # 2. Switch the stack to the analysis page — it appears instantly underneath
        self.root_stack.setCurrentIndex(_PAGE_ANALYSIS)

        # 3. Float the loader ON TOP of the stack, perfectly covering it
        self.loading_screen.setParent(self.root_stack)
        self.loading_screen.setGeometry(self.root_stack.rect())
        self.loading_screen.show()
        self.loading_screen.raise_()

        # 4. Fade the loader overlay out (1 → 0) while analysis page shows beneath
        self._loader_fade = QGraphicsOpacityEffect(self.loading_screen)
        self.loading_screen.setGraphicsEffect(self._loader_fade)
        self._loader_fade.setOpacity(1.0)

        self._anim_out = QPropertyAnimation(self._loader_fade, b"opacity")
        self._anim_out.setDuration(350)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def _on_crossfade_done():
            # Stop the timer — no need to keep painting a hidden widget
            self.loading_screen.timer.stop()
            # Remove the effect so rendering is clean next time
            self.loading_screen.setGraphicsEffect(None)
            # Put the loader back into the stack at its designated slot
            # so _transition_to_page can show it again on the next module open
            self.loading_screen.hide()
            self.root_stack.insertWidget(_PAGE_LOADING, self.loading_screen)

        self._anim_out.finished.connect(_on_crossfade_done)
        self._anim_out.start()

    def _on_module_load_error(self, module_id: str, error_msg: str) -> None:
        """Handles loading failures gracefully."""
        # Stop any running animations
        if (
            hasattr(self, "_anim_out")
            and self._anim_out.state() == QPropertyAnimation.State.Running
        ):
            self._anim_out.stop()
        if hasattr(self, "_anim_in") and self._anim_in.state() == QPropertyAnimation.State.Running:
            self._anim_in.stop()

        # Clean up a floating loader overlay if the crossfade was in-progress
        if (
            hasattr(self, "loading_screen")
            and self.loading_screen.parent() is self.root_stack
            and self.root_stack.indexOf(self.loading_screen) == -1
        ):
            self.loading_screen.timer.stop()
            self.loading_screen.setGraphicsEffect(None)
            self.loading_screen.hide()
            self.root_stack.insertWidget(_PAGE_LOADING, self.loading_screen)

        # Discard any pending warp-peaked state
        self._pending_manifest = None
        self._pending_panel_class = None

        # Force immediate return to home screen without animation so dialogs appear over the right UI
        self.root_stack.setCurrentIndex(_PAGE_HOME)
        self.root_stack.setGraphicsEffect(None)

        from biopro.ui.dialogs.error_report import ErrorReportDialog

        # Extract the exact exception message from the last line of the traceback if possible
        lines = [line.strip() for line in error_msg.strip().split("\n") if line.strip()]
        exc_msg = lines[-1] if lines else error_msg

        if "PermissionError: Security Block:" in exc_msg:
            # The module is untrusted, prompt user to lock it
            if self._on_trust_requested(module_id):
                # If they successfully trusted it, find the manifest and try loading again!
                manifests = self.module_manager.get_available_modules()
                manifest = next((m for m in manifests if m["id"] == module_id), None)
                if manifest:
                    self._open_module(manifest)
            else:
                # User declined or it failed, so we should discard the pending workflow
                self._pending_workflow_payload = None
                self._pending_workflow_filename = None
                self._pending_workflow_metadata = None
            return

        # Clear pending workflow state on any other load error
        self._pending_workflow_payload = None
        self._pending_workflow_filename = None
        self._pending_workflow_metadata = None

        error_data = {
            "plugin_id": module_id,
            "message": f"Failed to load module '{module_id}': {exc_msg}",
            "traceback": error_msg,
        }
        dialog = ErrorReportDialog(error_data, parent=self)
        dialog.exec()
        logger.error(f"Failed to load module {module_id}: {error_msg}")

    def _on_open_file(self) -> None:
        if self.root_stack.currentIndex() == _PAGE_HOME:
            self.status_bar.showMessage("Please select an analysis module first.")
            return
        if self.wizard_panel and hasattr(self.wizard_panel, "_open_file"):
            self.wizard_panel._open_file()

    def _show_about(self) -> None:
        # Dynamic Version from Config!
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "hologram_overlay") and self.hologram_overlay.isVisible():
            self.hologram_overlay.setGeometry(self.root_stack.geometry())

        if hasattr(self, "tutorial_overlay"):
            self.tutorial_overlay.setGeometry(self.analysis_page.rect())

        # Keep the floating loader overlay filling the stack during a crossfade
        if (
            hasattr(self, "loading_screen")
            and self.loading_screen.parent() is self.root_stack
            and self.loading_screen.isVisible()
            and self.root_stack.indexOf(self.loading_screen) == -1  # it's floating, not in stack
        ):
            self.loading_screen.setGeometry(self.root_stack.rect())

    def closeEvent(self, event):
        """Ensures all projects and plugins release resources before exit."""
        # 1. Stop background loading thread if active
        if (
            hasattr(self, "_module_thread")
            and self._module_thread
            and self._module_thread.isRunning()
        ):
            self._module_thread.quit()
            self._module_thread.wait()

        # 2. Stop any pending scientific analysis tasks
        from biopro.core.task_scheduler import task_scheduler

        task_scheduler.cancel_all()

        # 3. Shutdown active plugin if any
        if hasattr(self, "wizard_panel") and self.wizard_panel:
            try:
                if hasattr(self.wizard_panel, "shutdown"):
                    self.wizard_panel.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin: {e}")

        # 2. Close project
        if hasattr(self, "project_manager") and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")

        # Save geometry
        from biopro.core.preferences import core_preferences

        geom_hex = self.saveGeometry().toHex().data().decode("ascii")
        core_preferences.set("workspace_window_geometry", geom_hex)

        super().closeEvent(event)

    def return_to_hub(self):
        """Safely closes the active data and launches the main Project Hub window."""
        # 1. Cleanly clear the active project memory
        if hasattr(self, "project_manager") and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")

        # 2. THE FIX: Wake up the external DNA Hub window!
        if hasattr(self, "return_to_hub_callback") and self.return_to_hub_callback:
            self.return_to_hub_callback()

        # 3. THE FIX: Destroy this workspace window so it actually closes
        self.close()

    def _open_store(self):
        self.open_store_callback(self)

    def _open_ai_chat(self):
        """Show the floating AI Chat window."""
        logger.info("AI Chat button clicked.")
        # Get the currently loaded module directly
        mod_id = getattr(self, "current_module_id", None)

        try:
            if self._ai_window is None:
                logger.info("Creating new AI Chat window...")
                self._ai_window = AIChatWindow(parent=self, current_module_id=mod_id)
            else:
                logger.info("Refreshing existing AI Chat window...")
                # Update the module ID and refresh the UI checkboxes
                self._ai_window.update_module_context(mod_id)

            self._ai_window.show()
            self._ai_window.raise_()
            self._ai_window.activateWindow()
            logger.info("AI Chat window shown successfully.")
        except Exception as e:
            logger.error(f"Failed to open AI Chat: {e}")

    def refresh_ui(self):
        """Hot-reloads the module UI after the Store is closed."""
        self.home_screen.populate_modules(self.module_manager.get_available_modules())

    def _switch_theme(self, theme_path: Path) -> None:
        theme_manager.load_theme(theme_path)
        from biopro.core.preferences import core_preferences

        core_preferences.set("theme", str(theme_path.absolute()))

    def _on_trust_requested(self, module_id: str) -> bool:
        """Handle the user clicking the '⚠️ Lock' button on an untrusted plugin."""
        reply = QMessageBox.question(
            self,
            "Security: Trust Local Changes?",
            f"The module '{module_id}' has been modified locally.\n\n"
            "Do you trust these changes and want to lock them on this machine?\n\n"
            "By clicking 'Yes', BioPro will snapshot these files and trust them from now on.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.module_manager.trust_module(module_id):
                self.status_bar.showMessage(
                    f"Permanently trusted local changes for {module_id}.", 5000
                )
                # Refresh dashboard
                self.home_screen.populate_modules(self.module_manager.get_available_modules())
                return True
            else:
                QMessageBox.critical(
                    self, "Error", "Failed to trust module. Could not calculate hashes."
                )
        return False

    def _on_theme_changed(self) -> None:
        """Full workspace UI rebuild on theme swap."""
        from biopro.ui.theme import Strings

        # 0. Update Window Title
        project_name = self.project_manager.data.get("project_name", "Untitled Project")
        self.setWindowTitle(f"{Strings.APP_TITLE} — {project_name}")

        # Save where the user is currently looking!
        current_idx = self.root_stack.currentIndex()

        # 1. Update Main Window Base
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        self._apply_supplemental_qss()

        # 2. Update status bar and toolbar
        is_sw = "Galactic" in theme_manager.current_theme_name
        self.status_bar.setStyleSheet(
            f"background: {Colors.BG_DARK}; color: {Colors.FG_SECONDARY};"
            f" border-top: 1px solid {Colors.BORDER};"
            f" font-family: {Fonts.FAMILY_MONO if is_sw else 'inherit'};"
        )
        if hasattr(self, "analysis_toolbar"):
            self.analysis_toolbar._apply_theme_styles()

        # 3. Update status message
        is_sw = "Galactic" in theme_manager.current_theme_name
        if is_sw:
            self.status_bar.showMessage("SECTOR STATUS: READY | NAV-COMPUTER ONLINE")
        else:
            self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")

        # 4. Rebuild the Hub
        if hasattr(self, "home_screen"):
            self.root_stack.removeWidget(self.home_screen)
            self.home_screen.deleteLater()

        self.home_screen = HomeScreen()

        # Rewire signals
        self.home_screen.module_selected.connect(self._open_module)
        self.home_screen.return_to_hub_requested.connect(self.return_to_hub)
        self.home_screen.open_store_requested.connect(self._open_store)
        self.home_screen.open_ai_requested.connect(self._open_ai_chat)
        self.home_screen.workflow_selected.connect(self._load_workflow_from_dashboard)
        self.home_screen.workflow_settings_requested.connect(self._handle_workflow_settings)
        self.home_screen.trust_module_requested.connect(self._on_trust_requested)

        # Insert back into stack at index 0
        self.root_stack.insertWidget(_PAGE_HOME, self.home_screen)
        self.home_screen.populate_modules(self.module_manager.get_available_modules())
        self._refresh_hub_workflows()

        # Update active module UI, if present
        if hasattr(self, "wizard_panel") and self.wizard_panel is not None:
            self._refresh_widget_theme(self.wizard_panel)
            self.wizard_panel.update()

        # 4.5 Refresh Analysis Page and Tech Subtitle
        if hasattr(self, "analysis_page"):
            self.analysis_page.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        if hasattr(self, "aurebesh_lbl"):
            self.aurebesh_lbl.setStyleSheet(
                f"color: {Colors.ACCENT_PRIMARY}; font-size: 9px; padding-bottom: 2px; "
                f"background: {Colors.BG_DARK}; border-bottom: 1px solid {Colors.BORDER};"
            )

        # 5. Update Hologram Overlay
        if hasattr(self, "hologram_overlay"):
            if Colors.SCANLINE_OPACITY > 0:
                self.hologram_overlay.show()
                self.hologram_overlay.setGeometry(self.root_stack.geometry())
                self.hologram_overlay.raise_()
            else:
                self.hologram_overlay.hide()

        # Restore the view
        self.root_stack.setCurrentIndex(current_idx)

    def _refresh_widget_theme(self, widget: QWidget):
        """Recursively refreshes theme styles for a widget and its children."""
        if widget is None:
            return

        if hasattr(widget, "_apply_theme_styles"):
            widget._apply_theme_styles()
        elif hasattr(widget, "refresh_styles"):
            widget.refresh_styles()

        if widget.styleSheet():
            widget.setStyleSheet(widget.styleSheet())

        for child in widget.findChildren(QWidget):
            if hasattr(child, "_apply_theme_styles"):
                child._apply_theme_styles()
            elif hasattr(child, "refresh_styles"):
                child.refresh_styles()

            if child.styleSheet():
                child.setStyleSheet(child.styleSheet())
            child.update()

    def _push_history(self):
        """Captures a snapshot of the active module and pushes it to RAM."""
        # Check if we actually have a module ID loaded
        if (
            not self.wizard_panel
            or not hasattr(self.wizard_panel, "export_state")
            or not getattr(self, "current_module_id", None)
        ):
            return

        # Dynamically fetch the history for WHATEVER module is open!
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        history.push(self.wizard_panel.export_state())

    def trigger_undo(self):
        """Asks the HistoryManager to step back, then hands the old state to the plugin."""
        if (
            not self.wizard_panel
            or not hasattr(self.wizard_panel, "load_state")
            or not getattr(self, "current_module_id", None)
        ):
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
        if (
            not self.wizard_panel
            or not hasattr(self.wizard_panel, "load_state")
            or not getattr(self, "current_module_id", None)
        ):
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
                        with open(wf_file) as f:
                            data = json.load(f)
                            metadata = data.get("metadata", {})
                            workflows.append(
                                {
                                    "filename": wf_file.name,
                                    # Pull the module type directly from the file's saved metadata
                                    "module_id": metadata.get("module", "western_blot"),
                                    "name": metadata.get("name", wf_file.stem),
                                    "timestamp": metadata.get("timestamp", "Unknown Date"),
                                }
                            )
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

                QMessageBox.critical(
                    self, "Load Error", f"Module {module_id} is not currently installed."
                )
                return

            # 3. Store the pending payload for when the module is fully loaded
            self._pending_workflow_payload = payload
            self._pending_workflow_filename = filename

            # Extract metadata directly from the file to pass to the plugin
            import json

            try:
                wf_file = self.project_manager.project_dir / "workflows" / filename
                with open(wf_file) as f:
                    data = json.load(f)
                    self._pending_workflow_metadata = data.get("metadata", {})
            except Exception:
                self._pending_workflow_metadata = {}

            # 4. Open the module asynchronously
            self._open_module(manifest)

        except Exception as e:
            logger.exception("Failed to load workflow")
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(self, "Load Error", f"Could not load workflow:\n{str(e)}")

    def _handle_workflow_settings(self, module_id: str, filename: str) -> None:
        from biopro.ui.dialogs.workflow_settings import WorkflowSettingsDialog

        dialog = WorkflowSettingsDialog(self.project_manager, module_id, filename, parent=self)
        dialog.workflow_deleted.connect(self._refresh_hub_workflows)
        dialog.attachment_deleted.connect(self._refresh_hub_workflows)
        dialog.exec()

    # ─── ANIMATION ENGINE ───────────────────────────────────────────
    def _transition_to_page(self, page_index: int) -> None:
        """Fade the whole stack out then in when switching between Home and Loading pages.

        This is used for Home ↔ Loading transitions only.  The Loading → Analysis
        crossfade is handled separately by ``_crossfade_to_analysis()`` which keeps
        the loader animation running through the dissolve.
        """
        if self.root_stack.currentIndex() == page_index:
            return

        # Re-start the loader timer in case it was stopped from a previous load
        if page_index == _PAGE_LOADING:
            self.loading_screen.timer.start(16)

        # Attach opacity effect to the whole stack for simple page swaps
        self._fade_effect = QGraphicsOpacityEffect(self.root_stack)
        self.root_stack.setGraphicsEffect(self._fade_effect)

        self._anim_out = QPropertyAnimation(self._fade_effect, b"opacity")
        self._anim_out.setDuration(150)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InOutQuad)

        def _swap_and_fade_in():
            self.root_stack.setCurrentIndex(page_index)
            self._anim_in = QPropertyAnimation(self._fade_effect, b"opacity")
            self._anim_in.setDuration(150)
            self._anim_in.setStartValue(0.0)
            self._anim_in.setEndValue(1.0)
            self._anim_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self._anim_in.finished.connect(lambda: self.root_stack.setGraphicsEffect(None))
            self._anim_in.start()

        self._anim_out.finished.connect(_swap_and_fade_in)
        self._anim_out.start()

    # ────────────────────────────────────────────────────────────────
