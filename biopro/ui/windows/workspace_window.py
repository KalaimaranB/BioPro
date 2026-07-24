"""Workspace Window for BioPro."""

from __future__ import annotations

import logging

from PyQt6.QtCore import (
    QEasingCurve,
    QProcess,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
)
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.ui.components.toolbars import AnalysisToolBar
from biopro.ui.dashboards.workspace_dashboard import WorkspaceDashboard as HomeScreen
from biopro.ui.theme import Fonts, theme_manager
from biopro.ui.windows.workspace.hub_manager import HubManager
from biopro.ui.windows.workspace.menu_manager import MenuManager
from biopro.ui.windows.workspace.plugin_loader import PluginLoaderManager
from biopro.ui.windows.workspace.theme_manager import ThemeManager

logger = logging.getLogger(__name__)
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
_PAGE_HOME = 0
_PAGE_ANALYSIS = 1
_PAGE_LOADING = 2


class WorkspaceWindow(QMainWindow):
    """BioPro main application window."""

    APP_TITLE = "BioPro — Bio Analysis"
    DEFAULT_SIZE = QSize(1400, 860)

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
        self.setMinimumSize(1200, 800)
        self.theme_manager = ThemeManager(self)
        self.menu_manager = MenuManager(self)
        self.hub_manager = HubManager(self)
        self.plugin_manager = PluginLoaderManager(self)

        self.theme_manager.apply_supplemental_qss()
        from PyQt6.QtCore import QByteArray

        from biopro.core.preferences import core_preferences

        saved_geom = core_preferences.get("workspace_window_geometry")
        if saved_geom:
            self.restoreGeometry(QByteArray.fromHex(saved_geom.encode("ascii")))
        else:
            self.resize(self.DEFAULT_SIZE)

        self._setup_central_widget()
        self._setup_status_bar()
        self.menu_manager.setup_menu_bar()
        self.menu_manager.setup_shortcuts()
        self._connect_signals()
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, lambda _: self.refresh_ui())
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, lambda _: self.refresh_ui())
        self.home_screen.populate_modules(self.module_manager.get_available_modules())
        self.hub_manager.refresh_hub_workflows()
        self._ai_window = None
        self._module_thread = None
        self._module_worker = None
        self._pending_workflow_payload: dict | None = None
        self._pending_manifest: dict | None = None
        self._pending_panel_class: type | None = None
        self._last_import_file_count: int = 0
        self.hub_manager.show_home()
        theme_manager.theme_changed.connect(self.theme_manager.on_theme_changed)
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(400, self.hub_manager.maybe_start_core_intro)

    def _setup_central_widget(self) -> None:
        self.root_stack = QStackedWidget()
        self.home_screen = HomeScreen()
        self.root_stack.addWidget(self.home_screen)
        self.analysis_page = QWidget()
        self.analysis_page.setObjectName("WorkspaceAnalysisPage")
        ap_layout = QVBoxLayout(self.analysis_page)
        ap_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.setSpacing(0)
        self.analysis_toolbar = AnalysisToolBar("Analysis")
        self.analysis_toolbar.btn_home.clicked.connect(self.hub_manager.show_home)
        self.analysis_toolbar.btn_close_project.clicked.connect(self.return_to_hub)
        self.analysis_toolbar.btn_ai.clicked.connect(self.menu_manager.open_ai_chat)
        self.analysis_toolbar.btn_academy.clicked.connect(self.hub_manager.open_academy)
        self.aurebesh_lbl = QLabel("")
        self.aurebesh_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.aurebesh_lbl.setObjectName("AurebeshLabel")
        ap_layout.addWidget(self.analysis_toolbar)
        ap_layout.addWidget(self.aurebesh_lbl)
        self.wizard_panel = None
        self.main_module_container = QWidget()
        self.main_module_layout = QVBoxLayout(self.main_module_container)
        self.main_module_layout.setContentsMargins(0, 0, 0, 0)
        ap_layout.addWidget(self.main_module_container, stretch=1)
        from biopro.ui.effects.hologram_effect import HologramEffect

        self.hologram_overlay = HologramEffect(self.analysis_page)
        self.hologram_overlay.hide()
        self.root_stack.addWidget(self.analysis_page)
        from biopro.ui.wizards.tutorial_overlay import TutorialOverlay

        self.tutorial_overlay = TutorialOverlay(self.analysis_page)
        self.tutorial_overlay.hide()
        self.home_tutorial_overlay = TutorialOverlay(self.home_screen)
        self.home_tutorial_overlay.hide()
        self.tutorial_overlay.btn_next.clicked.connect(self._on_tutorial_next)
        self.tutorial_overlay.btn_close.clicked.connect(self._on_tutorial_skip)
        self.home_tutorial_overlay.btn_next.clicked.connect(self._on_tutorial_next)
        self.home_tutorial_overlay.btn_close.clicked.connect(self._on_tutorial_skip)
        self._tutorial_connections: dict = {}
        self._tutorial_last_step_id: str | None = None
        self._verification_wait: int = 0
        self.startTimer(100)
        self.loader_process = None
        self.setCentralWidget(self.root_stack)

    def _active_overlay(self):
        """Returns the TutorialOverlay that is currently relevant.

        Uses the home overlay when on the home screen, and the analysis
        overlay when a module is open.
        """
        from PyQt6.QtWidgets import QDialog

        store = self.findChild(QDialog, "PluginStoreDialog")
        if store and store.isVisible() and hasattr(store, "tutorial_overlay"):
            return store.tutorial_overlay
        if self.root_stack.currentIndex() == getattr(self, "_PAGE_HOME", 0):
            return self.home_tutorial_overlay
        return self.tutorial_overlay

    def _on_tutorial_next(self) -> None:
        """Called when the overlay Next button is clicked.

        For VerificationStep with allow_interaction=True the 'Next' button
        is labelled 'Check ✓'; clicking it runs the validator immediately
        rather than waiting for the background timer.

        For BranchingStep, the first option key maps to the target step_id;
        '__complete__' is a sentinel that completes the course.
        """
        from biopro.core.models.tutorial_models import BranchingStep, VerificationStep
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
        """Hide the active overlay and stop the current course.

        For the core intro specifically, sets a preference flag so the
        tour is not re-triggered on the next launch (user can still
        restart it from Help → Restart Onboarding Tour).
        """
        from biopro.core.tutorial_manager import global_tutorial_manager

        active_course = global_tutorial_manager.active_course
        self.home_tutorial_overlay.hide()
        self.tutorial_overlay.hide()
        if active_course and active_course.id == "core_intro_v1":
            from biopro.core.preferences import core_preferences

            core_preferences.set("core_intro_dismissed_once", True)
            self.status_bar.showMessage(
                "Tour skipped — restart anytime from Help → Restart Onboarding Tour.", 6000
            )
        global_tutorial_manager.active_course = None
        global_tutorial_manager.current_step = None
        wizard_panel = getattr(self, "wizard_panel", None)
        if wizard_panel:
            for canvas in wizard_panel.findChildren(QWidget, "FlowCanvas"):
                if hasattr(canvas, "set_guide_polygon"):
                    canvas.set_guide_polygon(None)

    def timerEvent(self, event) -> None:
        super().timerEvent(event)
        active_overlay = self._active_overlay()
        if hasattr(self, "home_tutorial_overlay") and self.home_tutorial_overlay.isVisible():
            store_active = active_overlay != self.home_tutorial_overlay
            self.home_tutorial_overlay.set_dark_mode(store_active)
        if not active_overlay.isVisible():
            return
        from biopro.core.models.tutorial_models import InteractionStep, VerificationStep
        from biopro.core.tutorial_manager import global_tutorial_manager

        step = global_tutorial_manager.current_step
        has_completion = (
            hasattr(active_overlay, "completion_container")
            and active_overlay.completion_container.isVisible()
        )
        if not step and (not has_completion):
            active_overlay.hide()
            return
        from PyQt6.QtWidgets import QDialog

        store = self.findChild(QDialog, "PluginStoreDialog")
        if store and store.isVisible():
            parent_page = store
        elif getattr(self, "root_stack", None) and self.root_stack.currentIndex() == getattr(
            self, "_PAGE_HOME", 0
        ):
            parent_page = self.home_screen
        else:
            parent_page = self.analysis_page
        new_geom = parent_page.rect()
        if active_overlay.geometry() != new_geom:
            active_overlay.setGeometry(new_geom)
            active_overlay.raise_()
        if not step:
            return
        current_id = step.id
        if current_id != self._tutorial_last_step_id:
            self._tutorial_last_step_id = current_id
            self._verification_wait = 0
            self._verification_attempts = 0
            active_overlay.raise_()
            active_overlay.render_step(step)
            guide_poly = getattr(step, "guide_poly", None)
            wizard_panel = getattr(self, "wizard_panel", None)
            if wizard_panel:
                for canvas in wizard_panel.findChildren(QWidget, "FlowCanvas"):
                    if hasattr(canvas, "set_guide_polygon"):
                        canvas.set_guide_polygon(guide_poly)
            if isinstance(step, InteractionStep) and step.target_widget_name:
                targets = parent_page.findChildren(QWidget, step.target_widget_name)
                for target_w in targets:
                    if hasattr(target_w, step.event_trigger):
                        obj_id = id(target_w)
                        conn_key = (
                            f"{step.id}__{step.target_widget_name}__{step.event_trigger}__{obj_id}"
                        )
                        if conn_key not in self._tutorial_connections:
                            print(f"DEBUG: Wiring InteractionStep signal {conn_key}")

                            def _make_advancer(sid: str):

                                def _advance(*_args):
                                    print(
                                        f"DEBUG: InteractionStep trigger fired for {sid}! current step is {(global_tutorial_manager.current_step.id if global_tutorial_manager.current_step else None)}"
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
        if isinstance(step, VerificationStep) and step.validator:
            self._verification_wait += 1
            if self._verification_wait > 20:
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
                    self._verification_attempts = 0
                    global_tutorial_manager.next_step(step.on_success_step_id)
                elif not getattr(step, "allow_interaction", False) and step.on_fail_step_id:
                    max_retries = getattr(step, "max_retries", 0)
                    attempts = getattr(self, "_verification_attempts", 0)
                    if attempts >= max_retries:
                        self._verification_attempts = 0
                        global_tutorial_manager.next_step(step.on_fail_step_id)
                    else:
                        self._verification_attempts = attempts + 1
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
        from PyQt6.QtCore import QRect

        targets: list[QWidget] = []
        search_root: QWidget = parent_page
        if search_root:
            for attr in ("target_widget_name",):
                name = getattr(step, attr, "")
                if name:
                    w = search_root.findChild(QWidget, name)
                    if w and w.isVisible():
                        targets.append(w)
            for name in getattr(step, "target_widget_names", []):
                by_name = [
                    w for w in search_root.findChildren(QWidget, name) if w and w.isVisible()
                ]
                if by_name:
                    targets.extend(by_name)
                else:
                    for w in search_root.findChildren(QWidget):
                        if w.property("tutorial_id") == name and w.isVisible():
                            targets.append(w)
        rects = []
        for w in targets:
            global_pos = w.mapToGlobal(w.rect().topLeft())
            local_pos = active_overlay.mapFromGlobal(global_pos)
            rects.append(QRect(local_pos, w.size()))
        active_overlay.set_targets(rects)

    def _setup_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setObjectName("WorkspaceStatusBar")
        is_sw = "Galactic" in theme_manager.current_theme_name
        theme_manager.apply_style(
            self.status_bar, f"font-family: {(Fonts.FAMILY_MONO if is_sw else 'inherit')};"
        )

        self.copyright_label = QLabel("© Kalaimaran Balasothy")
        self.copyright_label.setObjectName("CopyrightLabel")
        self.status_bar.addPermanentWidget(self.copyright_label)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("subtitle")
        self.status_bar.addPermanentWidget(self.zoom_label)
        self.status_bar.showMessage("Welcome to BioPro — choose a module to begin")

    def _connect_signals(self) -> None:
        self.home_screen.module_selected.connect(self.plugin_manager.open_module)
        self.home_screen.return_to_hub_requested.connect(self.return_to_hub)
        self.home_screen.open_store_requested.connect(self.hub_manager.open_store)
        self.home_screen.open_ai_requested.connect(self.menu_manager.open_ai_chat)
        self.home_screen.workflow_selected.connect(self.hub_manager.load_workflow_from_dashboard)
        self.home_screen.workflow_settings_requested.connect(
            self.hub_manager.handle_workflow_settings
        )
        self.home_screen.trust_module_requested.connect(self.hub_manager.on_trust_requested)
        self.home_screen.open_academy_requested.connect(self.hub_manager.open_academy_from_home)
        self.home_screen.open_academy_for_module_requested.connect(
            self.hub_manager.open_academy_for_module
        )

    def _on_open_file(self) -> None:
        if self.root_stack.currentIndex() == _PAGE_HOME:
            self.status_bar.showMessage("Please select an analysis module first.")
            return
        if self.wizard_panel and hasattr(self.wizard_panel, "_open_file"):
            self.wizard_panel._open_file()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "hologram_overlay") and self.hologram_overlay.isVisible():
            self.hologram_overlay.setGeometry(self.root_stack.geometry())
        if hasattr(self, "tutorial_overlay"):
            self.tutorial_overlay.setGeometry(self.analysis_page.rect())
        if hasattr(self, "home_tutorial_overlay"):
            self.home_tutorial_overlay.setGeometry(self.home_screen.rect())
        self._update_loader_geom()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._update_loader_geom()

    def _update_loader_geom(self):
        if (
            hasattr(self, "loader_process")
            and self.loader_process
            and (self.loader_process.state() != QProcess.ProcessState.NotRunning)
        ):
            geo = self.root_stack.mapToGlobal(self.root_stack.rect().topLeft())
            x, y, w, h = (geo.x(), geo.y(), self.root_stack.width(), self.root_stack.height())
            self.loader_process.write(f"GEOM {x} {y} {w} {h}\n".encode())

    def closeEvent(self, event):
        """Ensures all projects and plugins release resources before exit."""
        if (
            hasattr(self, "loader_process")
            and self.loader_process
            and (self.loader_process.state() != QProcess.ProcessState.NotRunning)
        ):
            self.loader_process.terminate()
            if not self.loader_process.waitForFinished(1000):
                self.loader_process.kill()
                self.loader_process.waitForFinished(500)
        if (
            hasattr(self, "_module_thread")
            and self._module_thread
            and self._module_thread.isRunning()
        ):
            self._module_thread.quit()
            self._module_thread.wait()
        from biopro.core.task_scheduler import task_scheduler

        task_scheduler.cancel_all()
        if hasattr(self, "wizard_panel") and self.wizard_panel:
            try:
                if hasattr(self.wizard_panel, "shutdown"):
                    self.wizard_panel.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin: {e}")
        if hasattr(self, "project_manager") and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        from biopro.core.preferences import core_preferences

        geom_hex = self.saveGeometry().toHex().data().decode("ascii")
        core_preferences.set("workspace_window_geometry", geom_hex)
        super().closeEvent(event)

    def return_to_hub(self):
        """Safely closes the active data and launches the main Project Hub window."""
        if hasattr(self, "project_manager") and self.project_manager:
            try:
                self.project_manager.close()
            except Exception as e:
                logger.error(f"Error closing project: {e}")
        if hasattr(self, "return_to_hub_callback") and self.return_to_hub_callback:
            self.return_to_hub_callback()
        self.close()

    def _on_wizard_state_changed(self) -> None:
        """Detects file imports via state_changed and emits FILE_IMPORTED.

        Checks if the wizard panel's state has more loaded files than last time
        and emits the event so WaitForEventStep(FILE_IMPORTED) auto-advances.
        """
        panel = getattr(self, "wizard_panel", None)
        if panel is None:
            return
        state = getattr(panel, "state", None) or {}
        if isinstance(state, dict) or hasattr(state, "get"):
            files = state.get("files") or state.get("loaded_files") or state.get("file_list") or []
        else:
            try:
                files = state.data.experiment.samples
            except AttributeError:
                files = []
        current_count = len(files) if hasattr(files, "__len__") else 0
        import logging

        logger = logging.getLogger("workspace_window")
        logger.warning(
            f"DEBUG _on_wizard_state_changed: current_count={current_count}, last={self._last_import_file_count}, files type={type(files)}"
        )
        if current_count > self._last_import_file_count:
            self._last_import_file_count = current_count
            logger.warning("DEBUG _on_wizard_state_changed: Emitting FILE_IMPORTED")

            def emit_imported():
                event_bus.emit(BioProEvent.FILE_IMPORTED, "")

            QTimer.singleShot(100, emit_imported)

    def refresh_ui(self):
        """Hot-reloads the module UI after the Store is closed."""
        self.home_screen.populate_modules(self.module_manager.get_available_modules())

    def _push_history(self):
        """Captures a snapshot of the active module and pushes it to RAM."""
        if (
            not self.wizard_panel
            or not hasattr(self.wizard_panel, "export_state")
            or (not getattr(self, "current_module_id", None))
        ):
            return
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        history.push(self.wizard_panel.export_state())

    def trigger_undo(self):
        """Asks the HistoryManager to step back, then hands the old state to the plugin."""
        if (
            not self.wizard_panel
            or not hasattr(self.wizard_panel, "load_state")
            or (not getattr(self, "current_module_id", None))
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
            or (not getattr(self, "current_module_id", None))
        ):
            return
        history = self.project_manager.history_manager.get_module_history(self.current_module_id)
        next_state = history.redo()
        if next_state is not None:
            self.wizard_panel.load_state(next_state)
            self.status_bar.showMessage("Redid last action.")
        else:
            self.status_bar.showMessage("Nothing to redo.")

    def _transition_to_page(self, page_index: int) -> None:
        """Fade the whole stack out then in when switching between Home and Loading pages.

        This is used for Home ↔ Loading transitions only.  The Loading → Analysis
        crossfade is handled separately by ``_crossfade_to_analysis()`` which keeps
        the loader animation running through the dissolve.
        """
        if self.root_stack.currentIndex() == page_index:
            return
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
