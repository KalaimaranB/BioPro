import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# CRITICAL: WebEngine initialization must happen BEFORE QApplication is created.
# This prevents "Symbol not found" and OpenGL context sharing errors.
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    # Fallback for environments without WebEngine (e.g. headless CI)
    pass

from pathlib import Path
import biopro.ui.theme

# --- STABILIZATION: Bootstrap Logging ---
def setup_logging():
    log_dir = Path.home() / ".biopro"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "biopro.log"
    
    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("--- BIOPRO SESSION STARTED ---")
    return log_file

# Delayed imports to allow logging to boot first
from biopro.core.module_manager import ModuleManager
from biopro.core.network_updater import NetworkUpdater
from biopro.ui.windows.project_launcher import ProjectLauncherWindow
from biopro.ui.dialogs.plugin_store import PluginStoreDialog
import biopro.ui.dialogs.save_workflow as dialogs

class BioProApp:
    def __init__(self):
        print("1. Initializing QApplication...")
        # Required for WebEngine to map graphics properly
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        self.app = QApplication(sys.argv)
        
        print("2. Booting Module Manager...")
        self.module_manager = ModuleManager()
        
        print("3. Booting Network Updater...")
        self.updater = NetworkUpdater()

    def run(self):
        print("4. Showing Hub Window...")
        self.show_hub()
        
        print("5. Starting PyQt Event Loop (App should stay open now)...")
        sys.exit(self.app.exec())

    def show_hub(self):
        self.hub = ProjectLauncherWindow(self.module_manager, self.updater, self.open_store, self.show_hub)
        self.hub.show()

    def open_store(self, parent_window):
        dialog = PluginStoreDialog(self.module_manager, self.updater, parent=parent_window)
        dialog.exec()
        self.module_manager.reload_modules()
        if hasattr(parent_window, 'refresh_ui'):
            parent_window.refresh_ui()

def main():
    log_file = setup_logging()
    
    # Handle SDK CLI commands if detected
    if len(sys.argv) > 1 and sys.argv[1] == "sdk":
        from biopro.sdk.sdk_cli import main as sdk_main
        sdk_main()
        return

    try:
        logger = logging.getLogger("BioPro")
        logger.info("--- APP BOOT SEQUENCE STARTED ---")
        app = BioProApp()
        app.run()
    except Exception as e:
        import traceback
        error_msg = f"FATAL BOOT ERROR:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        logging.critical(error_msg)
        
        # Show a critical error message if QApplication was successfully created
        # (Checking if 'app' exists in the local scope and has an instance)
        if QApplication.instance():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "BioPro Crash", f"BioPro failed to start.\n\nCheck the log at:\n{log_file}\n\nError: {str(e)}")
        
        sys.exit(1)

if __name__ == "__main__":
    main()