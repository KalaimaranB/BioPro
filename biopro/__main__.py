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

# 1. Force Python to print ALL logs to the terminal
logging.basicConfig(level=logging.DEBUG, 
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from biopro.core.module_manager import ModuleManager
from biopro.core.network_updater import NetworkUpdater
from biopro.ui.windows.project_launcher import ProjectLauncherWindow
from biopro.ui.dialogs.plugin_store import PluginStoreDialog
import biopro.ui.dialogs.save_workflow as dialogs
import biopro.ui.theme

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
    # Handle SDK CLI commands if detected
    if len(sys.argv) > 1 and sys.argv[1] == "sdk":
        from biopro.sdk.sdk_cli import main as sdk_main
        sdk_main()
        return

    print("--- APP BOOT SEQUENCE STARTED ---")
    app = BioProApp()
    app.run()

if __name__ == "__main__":
    main()