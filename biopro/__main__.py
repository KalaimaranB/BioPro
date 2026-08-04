import contextlib  # noqa: D100
import logging
import sys
from pathlib import Path


# --- STABILIZATION: Bootstrap Logging ---
# This MUST happen before any wasm/biopro imports
def setup_logging() -> Path:
    """Configure application logging and create the BioPro log file.

    Returns:
        Path: The path to the configured log file.
    """
    import logging.config
    from pathlib import Path

    log_dir = Path.home() / ".biopro"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "biopro.log"

    LOGGING_CONFIG = {  # noqa: N806
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s"},
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"  # noqa: E501
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": str(log_file),
                "mode": "w",
                "encoding": "utf-8",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
        "loggers": {
            "numba": {"level": "CRITICAL", "propagate": False},
            "matplotlib": {"level": "WARNING", "propagate": False},
            "PIL": {"level": "WARNING", "propagate": False},
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    logging.info("--- BIOPRO BOOTLOADER INITIALIZED ---")
    return log_file


def install_exception_hook():
    """Catch unhandled exceptions and route them through the diagnostic engine."""
    import sys

    from biopro.core.diagnostics import diagnostics

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Log it officially through our diagnostics engine
        diagnostics.report_error(
            message=f"Unhandled Exception: {exc_value}", exception=exc_value, fatal=True
        )

    sys.excepthook = handle_exception


class BioProApp:
    """Main application class for BioPro."""

    def __init__(self, module_manager, updater):
        """Initialize the Qt application and store dependencies.

        Parameters:
            module_manager: Manager used to load and reload application modules.
            updater: Service used to retrieve and update plugins.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication

        # CRITICAL: WebEngine initialization must happen BEFORE QApplication is created.
        with contextlib.suppress(ImportError):
            import PyQt6.QtWebEngineWidgets  # noqa: F401

        print("1. Initializing QApplication...")
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        self.app = QApplication(sys.argv)

        # CRITICAL: Theme is loaded from preferences BEFORE QApplication exists.
        # Now that QApplication exists, we must compile and apply the global stylesheet.
        from biopro.ui.theme import theme_manager

        theme_manager._apply_global_stylesheet()

        # --- BRANDING: Set Global Application Icon ---
        from PyQt6.QtGui import QIcon

        from biopro.core.resource_manager import resource_path

        # On macOS, the Dock icon is natively and perfectly managed by the .app bundle's Info.plist.
        # Setting a window icon with .icns can overwrite and reset the native round icon to a generic square if Qt's icns plugin is not loaded.  # noqa: E501
        if sys.platform != "darwin":
            icon_path = resource_path("icon.icns")
            if icon_path.exists():
                self.app.setWindowIcon(QIcon(str(icon_path)))

        self.module_manager = module_manager
        self.updater = updater

        # Apply SDK global styles (Fusion style engine, QPalette, QToolTip CSS).
        # This MUST be called after QApplication is created — the module-level call
        # in components.py fires too early (before QApplication exists) and is a no-op.
        try:
            from biopro_sdk.plugin.components import _apply_global_sdk_styles

            _apply_global_sdk_styles()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to apply SDK styles: {e}")

    def run(self) -> None:
        """Display the project hub and start the PyQt event loop."""
        print("4. Showing Hub Window...")
        self.show_hub()

        print("5. Starting PyQt Event Loop...")
        from biopro.core.task_scheduler import task_scheduler

        self.app.aboutToQuit.connect(task_scheduler.shutdown)

        sys.exit(self.app.exec())

    def show_hub(self) -> None:
        """Display the project launcher window."""
        from biopro.ui.windows.project_launcher import ProjectLauncherWindow

        self.hub = ProjectLauncherWindow(
            self.module_manager, self.updater, self.open_store, self.show_hub
        )
        self.hub.show()

    def open_store(self, parent_window) -> None:
        """Open the plugin store dialog and refresh the parent window after it closes.

        Parameters:
            parent_window: The window that owns the dialog and may be refreshed afterward.
        """
        from biopro.ui.dialogs.plugin_store import PluginStoreDialog

        dialog = PluginStoreDialog(self.module_manager, self.updater, parent=parent_window)
        dialog.exec()

        # Explicitly cleanup the tutorial overlay and delete the C++ dialog object
        # to guarantee we don't leak memory or dangling event bus subscriptions.
        dialog.tutorial_overlay._cleanup()
        dialog.deleteLater()

        self.module_manager.reload_modules()
        if hasattr(parent_window, "refresh_ui"):
            parent_window.refresh_ui()


def bootstrap_sdk():
    """Dynamic Bootstrapper for BioPro SDK.

    Checks ~/.biopro/sdk/ for a hot-patched/updated SDK.
    If it exists and is cryptographically verified against the Root Key,
    we prepend it to sys.path so the application runs the updated version.
    Otherwise, we fall back to the built-in system biopro-sdk.
    """
    import sys
    from pathlib import Path

    sdk_dir = Path.home() / ".biopro" / "sdk"
    if sdk_dir.exists():
        try:
            from biopro_sdk.host import TrustManager

            trust_mgr = TrustManager()
            result = trust_mgr.verify_plugin(sdk_dir)
            if result.success:
                sys.path.insert(0, str(sdk_dir / "src"))
                import logging

                logging.info(
                    f"🚀 [HOT PATCH] Successfully loaded cryptographically verified SDK from {sdk_dir}"  # noqa: E501
                )
                return True
            import logging

            logging.warning(
                f"⚠️ [HOT PATCH] SDK verification failed at {sdk_dir}: {result.error_message}. Falling back to default SDK."  # noqa: E501
            )
        except Exception as e:
            import logging

            logging.error(
                f"❌ [HOT PATCH] Failed to bootstrap dynamic SDK: {e}. Falling back to default SDK."
            )
    return False


def _run_smoke_test(argv: list[str]) -> int:  # noqa: C901, PLR0915
    """Run a smoke test for a specified plugin in a headless PyInstaller environment."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", dest="plugin_id")
    parser.add_argument("data_file", nargs="?", default=None)
    args, _ = parser.parse_known_args(argv[1:])

    logger = logging.getLogger("BioPro.SmokeTest")
    logger.info(f"--- SMOKE TEST SEQUENCE STARTED FOR {args.plugin_id} ---")

    # 1. Initialize Core Services
    from biopro.core.module_manager import ModuleManager
    from biopro.core.network_updater import NetworkUpdater

    updater = NetworkUpdater()
    module_manager = ModuleManager()

    # 2. Force install plugin if provided
    if args.plugin_id:
        logger.info(f"Attempting to download and install {args.plugin_id}...")
        registry = updater.fetch_remote_registry(updater.registry_url)
        plugin_info = registry.get("plugins", {}).get(args.plugin_id)

        if plugin_info:
            success, msg = updater.install_plugin(args.plugin_id, plugin_info)
            if not success:
                raise RuntimeError(f"Failed to install plugin: {msg}")

            # 2.5 Install Python dependencies for the newly downloaded plugin
            from biopro_sdk.plugin.manifest_parser import ManifestParser

            from biopro.core.package_manager import PackageManager

            pm = PackageManager()
            plugin_dir = updater.plugin_dir / args.plugin_id
            manifest_path = plugin_dir / "pyproject.toml"
            if manifest_path.exists():
                manifest = ManifestParser().parse_file(str(manifest_path))
                deps = manifest.get("python_dependencies")
                if deps is None:
                    deps_list = manifest.get("core_dependencies", [])
                    deps = dict.fromkeys(deps_list, "")

                if deps:
                    logger.info(
                        f"Installing {len(deps)} dependencies for {args.plugin_id} "
                        "into isolated venv..."
                    )
                    pm.resolve_and_install_all(deps, plugin_dir)

            # Re-scan installed modules
            module_manager.reload_modules()
        else:
            raise RuntimeError(f"Plugin {args.plugin_id} not found in remote registry.")

    # 3. Simulate UI Environment and Load Plugin
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(argv)

    if args.plugin_id:
        logger.info(
            "Loading plugin UI class to trigger all heavy imports (Numba, Matplotlib, C-Extensions)..."  # noqa: E501
        )

        # Temp Patch: Force trust the plugin to bypass Security Block during smoke testing
        module_manager.trust_module(args.plugin_id)

        # Prevent modal dialogs from hanging the headless runner
        from PyQt6.QtWidgets import QMessageBox

        def _mock_msgbox(*_args, **_kwargs):
            return None

        def _mock_question(*_args, **_kwargs):
            return QMessageBox.StandardButton.Yes

        QMessageBox.information = _mock_msgbox  # type: ignore[method-assign]
        QMessageBox.warning = _mock_msgbox  # type: ignore[method-assign]
        QMessageBox.critical = _mock_msgbox  # type: ignore[method-assign]
        QMessageBox.question = _mock_question  # type: ignore[method-assign]

        PanelClass = module_manager.load_module_ui(args.plugin_id)  # noqa: N806
        if PanelClass is None:
            raise RuntimeError(f"Plugin {args.plugin_id} exposes no UI class.")
        panel = PanelClass()

        if args.data_file and hasattr(panel, "load_workflow"):
            logger.info(f"Injecting test data file: {args.data_file}")

            try:
                # Monkeypatch fcs_io to explicitly fail if flowkit (daemon) is NOT used
                import biopro_plugins.flow_cytometry.analysis.fcs_io as fcs_io  # type: ignore[import-untyped, import-not-found]

                def _crash_fcsparser(*_args, **_kwargs):  # noqa: ARG001
                    raise RuntimeError(
                        "Smoke test explicitly failed: flowkit was not used! "
                        "Daemon virtual environment may be broken."
                    )

                fcs_io._load_with_fcsparser = _crash_fcsparser
                logger.info("Monkeypatched fcs_io to strictly enforce flowkit usage via daemon.")
            except ImportError:
                pass

            # If the plugin signals when async data is ready, wait for it
            if hasattr(panel, "data_ready"):
                logger.info("Hooking into plugin data_ready signal for delayed exit.")
                panel.data_ready.connect(app.quit)
                # Give it up to 15 seconds to load async data before forcing a quit
                QTimer.singleShot(15000, app.quit)

            panel.load_workflow(None, filename=args.data_file)

    logger.info("Smoke test passed all critical execution paths. Exiting cleanly.")

    # Allow event loop to tick once then quit successfully, unless we are waiting for data
    if not (args.plugin_id and args.data_file and hasattr(panel, "data_ready")):
        smoke_test_tick_ms = 1000
        QTimer.singleShot(smoke_test_tick_ms, app.quit)
    app.exec()
    return 0


def main():
    """Start the BioPro application or dispatch supported command-line modes.

    Handles SDK and AI server commands, optional plugin smoke tests, normal
    application initialization, and fatal startup errors.
    """
    log_file = setup_logging()
    bootstrap_sdk()

    # Handle SDK CLI commands if detected
    if len(sys.argv) > 1 and sys.argv[1] == "sdk":
        try:
            from biopro_sdk.sdk_cli import main as sdk_main

            sdk_main()
            return
        except Exception as e:
            logging.error(f"SDK Error: {e}")
            sys.exit(1)

    # Handle AI Server launch (used by the internal AI manager)
    if len(sys.argv) > 1 and sys.argv[1] == "ai-server":
        try:
            import llama_cpp.server.__main__ as ai_server

            # Remove 'ai-server' from args so llama_cpp.server sees its own flags
            sys.argv.pop(1)
            ai_server.main()
            return
        except Exception as e:
            logging.error(f"AI Server Startup Error: {e}")
            sys.exit(1)

    # Handle Smoke Test for PyInstaller validation (E2E CI/CD)
    if len(sys.argv) > 1 and sys.argv[1].startswith("--smoke-test"):
        try:
            sys.exit(_run_smoke_test(sys.argv))
        except Exception:
            import traceback

            logging.critical(f"SMOKE TEST FATAL CRASH:\n{traceback.format_exc()}")
            sys.exit(1)

    _start_application(log_file)


def _start_application(log_file: Path) -> None:

    try:
        logger = logging.getLogger("BioPro")
        logger.info("--- APP BOOT SEQUENCE STARTED ---")

        # Import core modules only after logging is setup
        from biopro.core.module_manager import ModuleManager
        from biopro.core.network_updater import NetworkUpdater

        module_manager = ModuleManager()
        updater = NetworkUpdater()

        # Initialize diagnostics and connect UI listener
        from biopro.core.event_bus import BioProEvent, event_bus

        # Restore Global Preferences (e.g. Theme)
        from biopro.core.preferences import core_preferences

        # Initialize global ToastManager for warnings
        from biopro.ui.dialogs.error_report import ErrorReportDialog
        from biopro.ui.theme import theme_manager

        saved_theme = core_preferences.get("theme")
        if saved_theme:
            theme_path = Path(saved_theme)
            if theme_path.exists():
                theme_manager.load_theme(theme_path)

        def on_error(error_data):
            # CRITICAL: We cannot show a QDialog if QApplication hasn't been created.
            # If it's a fatal error, we'll let the global exception handler in main() catch it
            # and show a native message box there.
            from PyQt6.QtWidgets import QApplication

            if not QApplication.instance():
                return

            dialog = ErrorReportDialog(error_data)
            dialog.exec()

        event_bus.subscribe(BioProEvent.ERROR_OCCURRED, on_error)
        install_exception_hook()

        app = BioProApp(module_manager, updater)
        app.run()
    except Exception as e:
        import traceback

        error_msg = f"FATAL BOOT ERROR:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        logging.critical(error_msg)

        from PyQt6.QtWidgets import QApplication, QMessageBox

        # Ensure we have a QApplication instance to show the message box
        _app = QApplication.instance()
        if not _app:
            # Create a dummy app just for the dialog
            _app = QApplication(sys.argv)

        QMessageBox.critical(
            None,
            "BioPro Crash",
            f"BioPro failed to start.\n\nError: {str(e)}\n\nCheck the log for details:\n{log_file}",
        )

        sys.exit(1)


if __name__ == "__main__":
    import contextlib
    import multiprocessing

    multiprocessing.freeze_support()
    with contextlib.suppress(RuntimeError):
        multiprocessing.set_start_method("spawn", force=True)

    main()
