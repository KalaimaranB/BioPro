"""Module Store and Update Dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QProgressBar, QMessageBox
)

from biopro.ui.theme import Colors, Fonts
from biopro.core.network_updater import NetworkUpdater, PluginInstallerWorker
from biopro.core.module_manager import ModuleManager

class StoreDialog(QDialog):
    def __init__(self, module_manager: ModuleManager, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.setWindowTitle("BioPro Module Store")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self.worker = None  # Holds the background download thread
        self._setup_ui()
        self._load_store_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("☁️ Plugin Store & Updates")
        header.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: bold;")
        layout.addWidget(header)
        
        # Scroll Area for Modules
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none;")
        
        self.store_container = QWidget()
        self.store_layout = QVBoxLayout(self.store_container)
        self.store_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.store_container)
        
        layout.addWidget(self.scroll)
        
        # Progress Bar (Hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        self.status_lbl = QLabel("")
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

    def _load_store_data(self):
        # 1. Fetch cloud registry
        registry = NetworkUpdater.fetch_registry()
        cloud_modules = registry.get("modules", [])
        
        # 2. Get currently installed modules
        installed_ids = [m["id"] for m in self.module_manager.get_available_modules()]
        
        # 3. Build UI Cards
        if not cloud_modules:
            self.store_layout.addWidget(QLabel("No modules found in the cloud registry."))
            return
            
        for mod in cloud_modules:
            is_installed = mod["id"] in installed_ids
            self._add_module_card(mod, is_installed)

    def _add_module_card(self, mod_data: dict, is_installed: bool):
        card = QWidget()
        card.setStyleSheet(f"background: {Colors.BG_DARK}; border-radius: 8px; padding: 10px;")
        layout = QHBoxLayout(card)
        
        # Info
        info_layout = QVBoxLayout()
        title = QLabel(f"{mod_data.get('icon', '📦')} {mod_data.get('name', 'Unknown')} (v{mod_data.get('version')})")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        desc = QLabel(mod_data.get('description', ''))
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
        info_layout.addWidget(title)
        info_layout.addWidget(desc)
        layout.addLayout(info_layout)
        
        # Install Button
        btn = QPushButton("Installed" if is_installed else "Download")
        btn.setEnabled(not is_installed)
        if not is_installed:
            btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; "
                f"border-radius: 4px; padding: 6px 15px; font-weight: bold; }}"
            )
            btn.clicked.connect(lambda checked, m=mod_data: self._install_module(m))
        
        layout.addWidget(btn)
        self.store_layout.addWidget(card)

    def _install_module(self, mod_data: dict):
        """Spawns the background thread to download and pip install the module."""
        download_url = mod_data.get("download_url")
        if not download_url:
            QMessageBox.warning(self, "Error", "No download link provided in registry.")
            return
            
        # UI Updates
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_lbl.show()
        for i in range(self.store_layout.count()):
            widget = self.store_layout.itemAt(i).widget()
            if widget: widget.setEnabled(False) # Disable store while downloading
            
        # Start Worker
        self.worker = PluginInstallerWorker(mod_data["id"], download_url, self.module_manager.user_plugins_dir)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._on_install_finished)
        self.worker.start()

    def _update_progress(self, val: int, msg: str):
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)

    def _on_install_finished(self, success: bool, msg: str):
        self.progress_bar.hide()
        self.status_lbl.setText(msg)
        for i in range(self.store_layout.count()):
            widget = self.store_layout.itemAt(i).widget()
            if widget: widget.setEnabled(True)
            
        if success:
            QMessageBox.information(self, "Success", f"{msg}\n\nPlease restart BioPro to load the new module.")
            self.accept()
        else:
            QMessageBox.critical(self, "Failed", msg)