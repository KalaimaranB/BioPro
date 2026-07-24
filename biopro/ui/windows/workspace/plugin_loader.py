"""Plugin Loader Manager for WorkspaceWindow."""

import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.ui.theme import theme_manager

logger = logging.getLogger(__name__)


class PluginUIWorker(QObject):
    """Worker to handle the slow import of plugin modules off the main thread."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, module_manager, module_id, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.module_id = module_id

    @pyqtSlot()
    def run(self):
        try:
            PanelClass = self.module_manager.load_module_ui(self.module_id)
            self.finished.emit(PanelClass)
        except Exception as e:
            import logging
            import traceback

            logging.getLogger(__name__).error(f"Failed to load module UI: {e}", exc_info=True)
            self.error.emit(traceback.format_exc())


class PluginLoaderManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def open_module(self, manifest: dict) -> None:
        """Triggers the Galactic transition and starts async module loading."""
        mw = self.main_window
        module_id = manifest["id"]
        module_name = manifest.get("name", "Analysis Module")
        logger.info(f"PluginLoader: Starting async load sequence for module '{module_id}'")

        from biopro.ui.widgets.galactic_loader import GalacticLoader

        # 1. Setup the QML Loader Widget
        if hasattr(mw, "loader_widget") and mw.loader_widget is not None:
            mw.loader_widget.deleteLater()
            mw.loader_widget = None

        mw.loader_widget = GalacticLoader(mw.root_stack)
        mw.loader_widget.set_module(module_name)
        mw.loader_widget.resize(mw.root_stack.size())
        mw.loader_widget.show()
        mw.loader_widget.raise_()

        # Connect the QML peak signal directly to instantiation
        mw.loader_widget.warp_out_finished.connect(self.on_warp_peaked)

        # 2. Cleanup existing thread if any
        if hasattr(mw, "_module_thread") and mw._module_thread and mw._module_thread.isRunning():
            mw._module_thread.quit()
            mw._module_thread.wait()

        # 3. Kick off the background worker
        mw._module_thread = QThread(mw)
        mw._module_worker = PluginUIWorker(mw.module_manager, module_id)
        mw._module_worker.moveToThread(mw._module_thread)

        mw._module_thread.started.connect(mw._module_worker.run)
        mw._module_worker.finished.connect(
            lambda PanelClass: self.on_module_loaded(manifest, PanelClass)
        )
        mw._module_worker.error.connect(lambda err: self.on_module_load_error(module_id, err))

        # Cleanup when done
        mw._module_worker.finished.connect(mw._module_thread.quit)
        mw._module_worker.error.connect(mw._module_thread.quit)

        mw._module_thread.start()

    def on_module_loaded(self, manifest: dict, PanelClass: type) -> None:
        mw = self.main_window
        module_id = manifest["id"]
        logger.info(
            f"PluginLoader: Successfully loaded UI class for module '{module_id}'. Waiting for GalacticLoader warp out..."
        )
        mw.current_module_id = module_id
        mw._pending_manifest = manifest
        mw._pending_panel_class = PanelClass

        # Step 1: Start warp-out immediately — animation keeps running natively via QML
        if hasattr(mw, "loader_widget") and mw.loader_widget:
            mw.loader_widget.warp_out()

    def on_warp_peaked(self) -> None:
        mw = self.main_window
        manifest = mw._pending_manifest
        PanelClass = mw._pending_panel_class
        mw._pending_manifest = None
        mw._pending_panel_class = None

        self.instantiate_module_panel(manifest, PanelClass)
        self.crossfade_to_analysis()

    def instantiate_module_panel(self, manifest: dict, PanelClass: type) -> None:
        mw = self.main_window
        module_id = manifest["id"]
        logger.info(f"PluginLoader: Instantiating UI panel for '{module_id}' and wiring events.")
        try:
            if mw.wizard_panel is not None:
                if hasattr(mw.wizard_panel, "cleanup"):
                    mw.wizard_panel.cleanup()
                mw.wizard_panel.setParent(None)
                mw.wizard_panel.deleteLater()

            mw.wizard_panel = PanelClass()
            assert mw.wizard_panel is not None
            mw.wizard_panel.project_manager = mw.project_manager

            mw.main_module_layout.addWidget(mw.wizard_panel)

            if hasattr(mw.wizard_panel, "canvas") and hasattr(
                mw.wizard_panel.canvas, "zoom_changed"
            ):
                mw.wizard_panel.canvas.zoom_changed.connect(
                    lambda z: mw.zoom_label.setText(f"{z * 100:.0f}%")
                )
            elif hasattr(mw.wizard_panel, "zoom_changed"):
                mw.wizard_panel.zoom_changed.connect(
                    lambda z: mw.zoom_label.setText(f"{z * 100:.0f}%")
                )

            mw.analysis_toolbar.set_title(
                manifest.get("icon", "📦"), manifest.get("name", "Analysis")
            )

            if "Galactic" in theme_manager.current_theme_name:
                mw.aurebesh_lbl.setText(
                    f"PROJECT: {mw.project_manager.data.get('project_name', 'UNKNOWN')} | NODE: {module_id.upper()} | ENCRYPTION: ACTIVE"
                )
                mw.aurebesh_lbl.show()
            else:
                mw.aurebesh_lbl.hide()

            if hasattr(mw.wizard_panel, "status_message"):
                mw.wizard_panel.status_message.connect(mw.status_bar.showMessage)
            if hasattr(mw.wizard_panel, "state_changed"):
                if hasattr(mw, "_push_history"):
                    mw.wizard_panel.state_changed.connect(mw._push_history)
                # Hook state_changed to detect file imports for the tutorial
                mw.wizard_panel.state_changed.connect(mw._on_wizard_state_changed)

            # Emit MODULE_OPENED for WaitForEventStep(MODULE_OPENED)
            event_bus.emit(BioProEvent.MODULE_OPENED, module_id)

            # Inject any pending workflow payload
            if (
                hasattr(mw, "_pending_workflow_payload")
                and mw._pending_workflow_payload is not None
            ):
                if hasattr(mw.wizard_panel, "load_workflow"):
                    import inspect

                    sig = inspect.signature(mw.wizard_panel.load_workflow)
                    kwargs = {}
                    if "filename" in sig.parameters:
                        kwargs["filename"] = getattr(mw, "_pending_workflow_filename", None)
                    if "metadata" in sig.parameters:
                        kwargs["metadata"] = getattr(mw, "_pending_workflow_metadata", None)

                    mw.wizard_panel.load_workflow(mw._pending_workflow_payload, **kwargs)
                    mw.status_bar.showMessage("Successfully loaded workflow payload.")
                mw._pending_workflow_payload = None
                mw._pending_workflow_filename = None
                mw._pending_workflow_metadata = None

            mw.status_bar.showMessage(f"{manifest.get('name')} — open a file to begin (Ctrl+O)")
            logger.info(f"PluginLoader: Module '{module_id}' is now fully initialized and active.")

        except Exception as e:
            import logging
            import traceback

            logging.getLogger(__name__).error(f"Failed to initialize module: {e}", exc_info=True)
            self.on_module_load_error(module_id, traceback.format_exc())

    def crossfade_to_analysis(self) -> None:
        mw = self.main_window
        # Switch the stack to the analysis page — it appears instantly underneath
        mw.root_stack.setCurrentIndex(1)  # _PAGE_ANALYSIS = 1

        # Fade out QML widget smoothly
        if hasattr(mw, "loader_widget") and mw.loader_widget:
            from PyQt6.QtCore import QPropertyAnimation
            from PyQt6.QtWidgets import QGraphicsOpacityEffect

            effect = QGraphicsOpacityEffect(mw.loader_widget)
            mw.loader_widget.setGraphicsEffect(effect)

            mw.loader_anim = QPropertyAnimation(effect, b"opacity")
            mw.loader_anim.setDuration(500)
            mw.loader_anim.setStartValue(1.0)
            mw.loader_anim.setEndValue(0.0)

            def on_fade_done():
                if hasattr(mw, "loader_widget") and mw.loader_widget:
                    mw.loader_widget.deleteLater()
                    mw.loader_widget = None

            mw.loader_anim.finished.connect(on_fade_done)
            mw.loader_anim.start()

    def on_module_load_error(self, module_id: str, error_msg: str) -> None:
        mw = self.main_window

        # Cleanup loader
        if hasattr(mw, "loader_widget") and mw.loader_widget:
            mw.loader_widget.deleteLater()
            mw.loader_widget = None

        # Discard any pending warp-peaked state
        mw._pending_manifest = None
        mw._pending_panel_class = None

        # Force immediate return to home screen without animation so dialogs appear over the right UI
        mw.root_stack.setCurrentIndex(0)  # _PAGE_HOME = 0
        mw.root_stack.setGraphicsEffect(None)

        from biopro.ui.dialogs.error_report import ErrorReportDialog

        # Extract the exact exception message from the last line of the traceback if possible
        lines = [line.strip() for line in error_msg.strip().split("\n") if line.strip()]
        exc_msg = lines[-1] if lines else error_msg

        if "PermissionError: Security Block:" in exc_msg:
            # The module is untrusted, prompt user to lock it
            if mw.hub_manager.on_trust_requested(module_id):
                # If they successfully trusted it, find the manifest and try loading again!
                manifests = mw.module_manager.get_available_modules()
                manifest = next((m for m in manifests if m["id"] == module_id), None)
                if manifest:
                    self.open_module(manifest)
            else:
                # User declined or it failed, so we should discard the pending workflow
                mw._pending_workflow_payload = None
                mw._pending_workflow_filename = None
                mw._pending_workflow_metadata = None
        else:
            # We explicitly ignore ModuleNotFoundError here since users might
            # uninstall a plugin without removing the hub metadata cache.
            # But we DO surface it if it's some other exception so they know it failed.
            if "ModuleNotFoundError" not in exc_msg:
                dialog = ErrorReportDialog(f"Failed to load module '{module_id}'", error_msg, mw)
                dialog.exec()
