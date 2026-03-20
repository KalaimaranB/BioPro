"""Module Store and Update Dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QProgressBar, QMessageBox
)

from biopro.ui.theme import Colors, Fonts
from biopro.core.network_updater import NetworkUpdater, PluginInstallerWorker
from biopro.core.module_manager import ModuleManager
from biopro.shared.ui.ui_components import PrimaryButton, SecondaryButton, DangerButton, ModuleCard, HeaderLabel

class StoreDialog(QDialog):
    def __init__(self, module_manager: ModuleManager, updater: NetworkUpdater, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.updater = updater

        self.setWindowTitle("BioPro Module Store")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self._setup_ui()
        self._load_store_data()

    def _setup_ui(self):
        # Fix the width so nothing gets cut off, but let it expand!
        self.setMinimumSize(550, 400)
        self.resize(750, 550) 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # Remove default window margins
        layout.setSpacing(0)
        
        # --- A Fancy Header Banner ---
        header_banner = QWidget()
        header_banner.setStyleSheet(f"background-color: {Colors.BG_MEDIUM}; border-bottom: 1px solid {Colors.BORDER};")
        header_layout = QHBoxLayout(header_banner)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        header_title = QLabel("☁️ Plugin Store & Updates")
        header_title.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 800; color: {Colors.FG_PRIMARY};")
        header_layout.addWidget(header_title)
        
        layout.addWidget(header_banner)
        
        # --- The Scroll Area ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.store_container = QWidget()
        self.store_container.setStyleSheet("background: transparent;")
        self.store_layout = QVBoxLayout(self.store_container)
        self.store_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.store_layout.setContentsMargins(20, 20, 20, 20) # Add breathing room around the cards
        self.store_layout.setSpacing(15)
        
        self.scroll.setWidget(self.store_container)
        layout.addWidget(self.scroll)
        
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; padding: 10px;")
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _load_store_data(self):
        # 1. Clear existing cards if we are refreshing the UI
        for i in reversed(range(self.store_layout.count())): 
            widget = self.store_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 2. Use our new Logic Engine to get the exact state of every plugin
        inventory = self.updater.evaluate_store_state()
        
        if not inventory:
            self.store_layout.addWidget(QLabel("Could not connect to the cloud registry."))
            return
            
        # 3. Build UI Cards
        for plugin_id, data in inventory.items():
            self._add_module_card(plugin_id, data)

    def _add_module_card(self, plugin_id: str, data: dict):
        mod_data = data["info"]
        state = data["state"]
        local_ver = data["local_version"]

        # 1. Use our new standardized card! (No CSS needed)
        card = ModuleCard()
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # --- Info Section ---
        info_layout = QVBoxLayout()
        title_text = f"{mod_data.get('icon', '📦')} {mod_data.get('name', 'Unknown')}"
        
        if local_ver:
            title_text += f" (Installed: v{local_ver} | Latest: v{mod_data.get('version')})"
        else:
            title_text += f" (v{mod_data.get('version')})"
            
        title = QLabel(title_text)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        desc = QLabel(mod_data.get('description', ''))
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
        
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        layout.addLayout(info_layout)
        
        # --- Dynamic Button Section ---
        btn_layout = QHBoxLayout()
        
        if state == "INCOMPATIBLE":
            btn = SecondaryButton(f"Requires Core v{mod_data.get('min_core_version')}")
            btn.setEnabled(False)
            btn_layout.addWidget(btn)
            
        elif state == "INSTALL":
            btn = PrimaryButton("Download")
            btn.clicked.connect(lambda checked, pid=plugin_id, m=mod_data: self._install_module(pid, m))
            btn_layout.addWidget(btn)
            
        elif state == "UPDATE":
            # Using Primary for Update, Danger for Remove
            btn = PrimaryButton("Update Available")
            btn.clicked.connect(lambda checked, pid=plugin_id, m=mod_data: self._install_module(pid, m))
            
            rm_btn = DangerButton("Remove")
            rm_btn.clicked.connect(lambda checked, pid=plugin_id: self._remove_module(pid))
            
            btn_layout.addWidget(btn)
            btn_layout.addWidget(rm_btn)
            
        elif state == "UP_TO_DATE":
            lbl = QLabel("✓ Up to Date")
            lbl.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; padding-right: 10px;")
            
            rm_btn = DangerButton("Remove")
            rm_btn.clicked.connect(lambda checked, pid=plugin_id: self._remove_module(pid))
            
            btn_layout.addWidget(lbl)
            btn_layout.addWidget(rm_btn)
            
        layout.addLayout(btn_layout)
        self.store_layout.addWidget(card)


    def _install_module(self, plugin_id: str, mod_data: dict):
        """Uses the Logic Engine to install the plugin and update the tracker."""
        from PyQt6.QtWidgets import QApplication
        
        # Briefly show the user that something is happening
        self.status_lbl.setText(f"Installing {mod_data.get('name')}...")
        self.status_lbl.show()
        QApplication.processEvents() # Forces the UI to visually update immediately
        
        # Let the NetworkUpdater handle the download AND the json tracking
        success, msg = self.updater.install_plugin(plugin_id, mod_data)
        
        self.status_lbl.hide()
        
        if success:
            # Instantly redraw the store. The button will magically turn into "✓ Up to Date"!
            self._load_store_data() 
        else:
            QMessageBox.critical(self, "Installation Failed", msg)

    def _remove_module(self, plugin_id: str):
        success, msg = self.updater.remove_plugin(plugin_id)
        if success:
            self._load_store_data() # Refresh the UI instantly!
        else:
            QMessageBox.critical(self, "Error", msg)