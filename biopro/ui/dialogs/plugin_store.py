"""Module Store and Update Dialog."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QProgressBar, QMessageBox,
    QSplitter, QLineEdit, QListWidget, QListWidgetItem, QGridLayout
)

from biopro.ui.theme import Colors, Fonts
from biopro.core.network_updater import NetworkUpdater, PluginInstallerWorker
from biopro.core.module_manager import ModuleManager
from biopro.core.event_bus import event_bus, BioProEvent
from biopro.sdk.ui import PrimaryButton, SecondaryButton, DangerButton, ModuleCard, HeaderLabel

class PluginStoreDialog(QDialog):
    def __init__(self, module_manager: ModuleManager, updater: NetworkUpdater, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.updater = updater

        self.setWindowTitle("BioPro Module Store")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self._setup_ui()
        self._load_store_data()
        
        # Subscribe to the nervous system
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, self._on_plugin_event)
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, self._on_plugin_event)

    def _on_plugin_event(self, _id: str):
        """React to external plugin changes."""
        self._load_store_data()

    def closeEvent(self, event):
        """Cleanup subscriptions on close."""
        event_bus.unsubscribe(BioProEvent.PLUGIN_INSTALLED, self._on_plugin_event)
        event_bus.unsubscribe(BioProEvent.PLUGIN_REMOVED, self._on_plugin_event)
        super().closeEvent(event)

    def _setup_ui(self):
        self.setMinimumSize(850, 600)
        self.resize(950, 700) 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Top Search & Header Bar ---
        header_banner = QWidget()
        header_banner.setStyleSheet(f"background-color: {Colors.BG_MEDIUM}; border-bottom: 2px solid {Colors.BORDER};") # Slab style border
        header_layout = QHBoxLayout(header_banner)
        header_layout.setContentsMargins(20, 8, 20, 8) # Tighter vertical padding
        
        header_title = QLabel("☁️ Marketplace")
        header_title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {Colors.FG_PRIMARY};")
        header_layout.addWidget(header_title)
        
        header_layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins by name, tag, or author...")
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{ 
                background: {Colors.BG_DARKEST}; 
                border: 1px solid {Colors.BORDER}; 
                border-radius: 6px; 
                padding: 5px 12px;
                color: {Colors.FG_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit:focus {{ border: 1px solid {Colors.ACCENT_PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)
        
        layout.addWidget(header_banner)
        
        # --- Main Splitter (Sidebar | Content) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background: {Colors.BORDER}; }}")
        
        # 1. Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(230) # Wider to prevent "Utilities" clipping
        self.sidebar.setStyleSheet(f"background: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 20, 8, 20)
        sidebar_layout.setSpacing(6)
        
        sidebar_label = QLabel("DISCOVER")
        sidebar_label.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {Colors.FG_DISABLED}; margin-left: 5px;")
        sidebar_layout.addWidget(sidebar_label)
        
        self.filter_list = QListWidget()
        self.filter_list.setStyleSheet(f"""
            QListWidget {{ 
                background: transparent; 
                border: none; 
                outline: none;
            }}
            QListWidget::item {{ 
                padding: 10px 14px; 
                border-radius: 6px; 
                color: {Colors.FG_PRIMARY};
                margin-bottom: 4px;
            }}
            QListWidget::item:selected {{ 
                background: {Colors.ACCENT_PRIMARY}; 
                color: {Colors.BG_DARKEST}; 
                font-weight: bold;
            }}
            QListWidget::item:hover:!selected {{ 
                background: {Colors.BG_MEDIUM}; 
            }}
        """)
        
        filters = [
            ("All Plugins", "all"),
            ("Available Updates", "updates"),
            ("Installed", "installed"),
            ("Verified Only", "verified"),
            ("Analysis Tools", "cat_analysis"),
            ("Utilities", "cat_utility")
        ]
        
        for label, data in filters:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.filter_list.addItem(item)
            
        self.filter_list.setCurrentRow(0)
        self.filter_list.currentRowChanged.connect(self._on_filter_changed)
        sidebar_layout.addWidget(self.filter_list)
        
        sidebar_layout.addStretch()
        self.splitter.addWidget(self.sidebar)
        
        # 2. Content Area
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.store_grid_widget = QWidget()
        self.store_grid_widget.setStyleSheet("background: transparent;")
        self.store_grid = QGridLayout(self.store_grid_widget)
        self.store_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.store_grid.setContentsMargins(20, 20, 20, 20)
        self.store_grid.setSpacing(20)
        
        self.scroll.setWidget(self.store_grid_widget)
        content_layout.addWidget(self.scroll)
        
        self.splitter.addWidget(self.content_container)
        layout.addWidget(self.splitter)
        
        # Status Label at Bottom
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; padding: 10px; background: {Colors.BG_MEDIUM}; border-top: 1px solid {Colors.BORDER};")
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)
    
    def _on_search_changed(self, text: str):
        self._load_store_data()

    def _on_filter_changed(self, row: int):
        self._load_store_data()

    def _load_store_data(self):
        # 1. Clear grid
        for i in reversed(range(self.store_grid.count())): 
            widget = self.store_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 2. Get inventory
        inventory = self.updater.evaluate_store_state()
        if not inventory:
            self.store_grid.addWidget(QLabel("Could not connect to the cloud registry."), 0, 0)
            return

        # 3. Apply Filters
        search_text = self.search_input.text().lower()
        filter_item = self.filter_list.currentItem()
        filter_type = filter_item.data(Qt.ItemDataRole.UserRole) if filter_item else "all"

        filtered_items = []
        for plugin_id, data in inventory.items():
            mod_data = data["info"]
            state = data["state"]
            is_verified = data["is_verified"]
            
            # Search Filter
            match_search = (
                search_text in plugin_id.lower() or 
                search_text in mod_data.get("name", "").lower() or 
                search_text in mod_data.get("description", "").lower() or
                search_text in mod_data.get("author", "").lower()
            )
            if not match_search: continue

            # Sidebar Filter
            if filter_type == "updates" and state != "UPDATE": continue
            if filter_type == "installed" and not data.get("local_version"): continue
            if filter_type == "verified" and not is_verified: continue
            if filter_type.startswith("cat_"):
                target_cat = filter_type.split("_")[1]
                if mod_data.get("category", "").lower() != target_cat: continue

            filtered_items.append((plugin_id, data))

        # 4. Populate Grid (2 columns for better readability)
        for i, (plugin_id, data) in enumerate(filtered_items):
            row, col = i // 2, i % 2
            card = self._create_store_card(plugin_id, data)
            self.store_grid.addWidget(card, row, col)

    def _create_store_card(self, plugin_id: str, data: dict):
        mod_data = data["info"]
        state = data["state"]
        local_ver = data["local_version"]
        is_verified = data.get("is_verified", False)

        card = ModuleCard() # Base styling
        card.setMinimumWidth(350) 
        
        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)
        
        # Header: Icon and Name
        header = QHBoxLayout()
        icon_lbl = QLabel(mod_data.get('icon', '📦'))
        icon_lbl.setStyleSheet("font-size: 24px;")
        header.addWidget(icon_lbl)
        
        name_layout = QVBoxLayout()
        name_lbl = QLabel(mod_data.get('name', 'Unknown'))
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; border: none;")
        name_layout.addWidget(name_lbl)
        
        author_lbl = QLabel(f"by {mod_data.get('author', 'Community')}")
        author_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;")
        name_layout.addWidget(author_lbl)
        header.addLayout(name_layout)
        header.addStretch()
        
        # Badge for Verified
        if is_verified:
            badge = QLabel("🛡️ VERIFIED")
            badge.setStyleSheet(f"background: {Colors.ACCENT_SUCCESS}22; color: {Colors.ACCENT_SUCCESS}; font-size: 9px; font-weight: 900; padding: 4px 8px; border-radius: 4px; border: 1px solid {Colors.ACCENT_SUCCESS}44;")
            header.addWidget(badge)
            
        main_layout.addLayout(header)
        
        # Description (Fixed height to prevent jumping)
        desc = QLabel(mod_data.get('description', ''))
        desc.setWordWrap(True)
        desc.setFixedHeight(40) # 2 lines roughly
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; border: none; font-size: 12px;")
        main_layout.addWidget(desc)
        
        # Metadata / Actions Row
        bottom_row = QHBoxLayout()
        
        ver_info = f"v{mod_data.get('version')}"
        if local_ver and local_ver != mod_data.get('version'):
            ver_info = f"v{local_ver} ➔ v{mod_data.get('version')}"
        
        ver_lbl = QLabel(ver_info)
        ver_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_DISABLED}; border: none;")
        bottom_row.addWidget(ver_lbl)
        bottom_row.addStretch()
        
        # Dynamic Actions
        if state == "INCOMPATIBLE":
            btn = SecondaryButton(f"Incompatible")
            btn.setToolTip(f"Requires core v{mod_data.get('min_core_version')}")
            btn.setEnabled(False)
            bottom_row.addWidget(btn)
        elif state == "INSTALL":
            btn = PrimaryButton("Install")
            btn.clicked.connect(lambda: self._install_module(plugin_id, mod_data))
            bottom_row.addWidget(btn)
        elif state == "UPDATE":
            upd_btn = PrimaryButton("Update")
            upd_btn.clicked.connect(lambda: self._install_module(plugin_id, mod_data))
            
            rm_btn = DangerButton("×")
            rm_btn.setToolTip("Remove Plugin")
            rm_btn.setFixedSize(30, 30)
            rm_btn.clicked.connect(lambda: self._remove_module(plugin_id))
            
            bottom_row.addWidget(rm_btn)
            bottom_row.addWidget(upd_btn)
        elif state == "UP_TO_DATE":
            ok_lbl = QLabel("✓ Installed")
            ok_lbl.setStyleSheet(f"color: {Colors.ACCENT_SUCCESS}; font-size: 11px; font-weight: bold; margin-right: 5px;")
            bottom_row.addWidget(ok_lbl)
            
            rm_btn = DangerButton("Remove")
            rm_btn.clicked.connect(lambda: self._remove_module(plugin_id))
            bottom_row.addWidget(rm_btn)
            
        main_layout.addLayout(bottom_row)
        return card


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
            # We no longer need to call self._load_store_data() here!
            # The Event Bus will fire and we will catch it in _on_plugin_event.
            pass 
        else:
            QMessageBox.critical(self, "Installation Failed", msg)

    def _remove_module(self, plugin_id: str):
        success, msg = self.updater.remove_plugin(plugin_id)
        if not success:
            QMessageBox.critical(self, "Error", msg)