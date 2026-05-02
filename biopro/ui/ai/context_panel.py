from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QScrollArea, QCheckBox
)
from biopro.ui.theme import Colors
from biopro.sdk.core.ai import AIAssistant

class ContextPanel(QWidget):
    """Integrated sidebar for managing AI context."""
    selection_changed = pyqtSignal(list)

    def __init__(self, parent, assistant: AIAssistant):
        super().__init__(parent)
        self.assistant = assistant
        self.plugin_id = None
        self.include_core = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header
        header = QLabel("DOCUMENT CONTEXT")
        header.setStyleSheet(f"font-weight: bold; color: {Colors.ACCENT_PRIMARY}; font-size: 10px; letter-spacing: 1px;")
        layout.addWidget(header)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter docs...")
        self.search_bar.setStyleSheet(f"background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 4px; font-size: 11px;")
        self.search_bar.textChanged.connect(self._filter_files)
        layout.addWidget(self.search_bar)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Footer
        self.stats_lbl = QLabel("Usage: 0KB / 20KB (0%)")
        self.stats_lbl.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 10px;")
        layout.addWidget(self.stats_lbl)

    def refresh(self, plugin_id: str, include_core: bool):
        """Populate the sidebar with available documentation files.
        
        Args:
            plugin_id (str): The ID of the currently active plugin.
            include_core (bool): Whether to show core system documentation.
        """
        self.plugin_id = plugin_id
        self.include_core = include_core
        
        # Clear current
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.takeAt(i)
            if item.widget(): item.widget().deleteLater()
            
        # Discover all
        _, docs = self.assistant._gather_context("", plugin_id, include_core, discover_only=True)
        
        core_docs = [d for d in docs if d["type"] == "core"]
        plugin_docs = [d for d in docs if d["type"] == "plugin"]

        def add_group(title: str, docs_list: list):
            if not docs_list: return
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-size: 9px; font-weight: bold; margin-top: 5px; background: {Colors.BG_DARKEST}; padding: 2px;")
            self.container_layout.addWidget(lbl)
            
            pinned = ["01_User_Guide.md", "02_Getting_Started.md", "README.md"]
            for d in sorted(docs_list, key=lambda x: x["name"]):
                name = d["name"]
                size_kb = d["size"] / 1024
                cb = QCheckBox(f"{name} ({size_kb:.1f} KB)")
                cb.setProperty("filename", name)
                cb.setProperty("file_size", d["size"])
                cb.setChecked(name in pinned)
                cb.setStyleSheet(f"QCheckBox {{ color: {Colors.FG_PRIMARY}; font-size: 11px; padding: 1px; }}")
                cb.stateChanged.connect(self._on_selection_changed)
                self.container_layout.addWidget(cb)

        add_group("🏛 CORE SYSTEM", core_docs)
        add_group(f"🔌 PLUGIN: {plugin_id.upper() if plugin_id else 'NONE'}", plugin_docs)
            
        self.container_layout.addStretch()
        self._on_selection_changed()

    def _filter_files(self, text):
        text = text.lower()
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.setVisible(text in widget.property("filename").lower())

    def _on_selection_changed(self):
        selected_filenames = []
        total_bytes = 0
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selected_filenames.append(widget.property("filename"))
                total_bytes += widget.property("file_size")
        
        kb_used = total_bytes / 1024
        percent = min(100, (total_bytes / 20000) * 100)
        self.stats_lbl.setText(f"Usage: {kb_used:.1f}KB / 20KB ({percent:.0f}%)")
        self.stats_lbl.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY if percent < 90 else 'red'}; font-size: 10px;")
        self.selection_changed.emit(selected_filenames)

    def get_selected_files(self):
        """Return a list of filenames currently checked in the UI.
        
        Returns:
            list[str]: List of filenames to be included in the AI context.
        """
        selected = []
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selected.append(widget.property("filename"))
        return selected
