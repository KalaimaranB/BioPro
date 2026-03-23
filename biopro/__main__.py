import sys
import logging
from PyQt6.QtWidgets import QApplication

# 1. Force Python to print ALL logs to the terminal
logging.basicConfig(level=logging.DEBUG, 
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

from biopro.core.module_manager import ModuleManager
from biopro.core.network_updater import NetworkUpdater
from biopro.ui.hub_window import HubWindow
from biopro.ui.store_dialog import StoreDialog
import biopro.ui.dialogs 
import biopro.ui.theme

class BioProApp:
    def __init__(self):
        print("1. Initializing QApplication...")
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
        self.hub = HubWindow(self.module_manager, self.updater, self.open_store, self.show_hub)
        self.hub.show()

    def open_store(self, parent_window):
        dialog = StoreDialog(self.module_manager, self.updater, parent=parent_window)
        dialog.exec()
        self.module_manager.reload_modules()
        if hasattr(parent_window, 'refresh_ui'):
            parent_window.refresh_ui()

def main():
    print("--- APP BOOT SEQUENCE STARTED ---")
    app = BioProApp()
    app.run()

if __name__ == "__main__":
    main()