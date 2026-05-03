import sys
import logging
from pathlib import Path

# --- STABILIZATION: Bootstrap Logging ---
# This MUST happen before any wasm/biopro imports
def setup_logging():
    import logging.config
    log_dir = Path.home() / ".biopro"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "biopro.log"
    
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'formatter': 'detailed',
                'filename': str(log_file),
                'mode': 'w',
                'encoding': 'utf-8',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
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
            message=f"Unhandled Exception: {exc_value}",
            exception=exc_value,
            fatal=True
        )

    sys.excepthook = handle_exception

class BioProApp:
    def __init__(self, module_manager, updater):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        # CRITICAL: WebEngine initialization must happen BEFORE QApplication is created.
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            pass

        print("1. Initializing QApplication...")
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        self.app = QApplication(sys.argv)
        
        # --- BRANDING: Set Global Application Icon ---
        from biopro.core.resource_manager import resource_path
        from PyQt6.QtGui import QIcon
        icon_path = resource_path("icon.icns")
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))
        else:
            print(f"Warning: Icon not found at {icon_path}")
        
        self.module_manager = module_manager
        self.updater = updater

    def run(self):
        print("4. Showing Hub Window...")
        self.show_hub()
        
        print("5. Starting PyQt Event Loop...")
        sys.exit(self.app.exec())

    def show_hub(self):
        from biopro.ui.windows.project_launcher import ProjectLauncherWindow
        self.hub = ProjectLauncherWindow(self.module_manager, self.updater, self.open_store, self.show_hub)
        self.hub.show()

    def open_store(self, parent_window):
        from biopro.ui.dialogs.plugin_store import PluginStoreDialog
        dialog = PluginStoreDialog(self.module_manager, self.updater, parent=parent_window)
        dialog.exec()
        self.module_manager.reload_modules()
        if hasattr(parent_window, 'refresh_ui'):
            parent_window.refresh_ui()

def main():
    log_file = setup_logging()
    
    # Handle SDK CLI commands if detected
    if len(sys.argv) > 1 and sys.argv[1] == "sdk":
        try:
            from biopro.sdk.sdk_cli import main as sdk_main
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

    try:
        logger = logging.getLogger("BioPro")
        logger.info("--- APP BOOT SEQUENCE STARTED ---")
        
        # Import core modules only after logging is setup
        from biopro.core.module_manager import ModuleManager
        from biopro.core.network_updater import NetworkUpdater
        
        module_manager = ModuleManager()
        updater = NetworkUpdater()
        
        # Initialize diagnostics and connect UI listener
        from biopro.core.diagnostics import diagnostics
        from biopro.core.event_bus import event_bus, BioProEvent
        from biopro.ui.dialogs.error_report import ErrorReportDialog
        
        def on_error(error_data):
            # CRITICAL: We cannot show a QDialog if QApplication hasn't been created.
            # If it's a fatal error, we'll let the global exception handler in main() catch it
            # and show a native message box there.
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
            f"BioPro failed to start.\n\nError: {str(e)}\n\nCheck the log for details:\n{log_file}"
        )
        
        sys.exit(1)

if __name__ == "__main__":
    main()