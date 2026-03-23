# biopro/ui/hub_widgets.py
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from biopro.ui.theme import Colors

class WorkflowCard(QFrame):
    """A visual card representing a saved workflow."""
    def __init__(self, metadata: dict, on_load_callback):
        super().__init__()
        self.metadata = metadata
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Swapped BG_SECONDARY for BG_MEDIUM and BORDER
        self.setStyleSheet(
            f"QFrame {{ "
            f"  background-color: {Colors.BG_MEDIUM}; "
            f"  border: 1px solid {Colors.BORDER}; "
            f"  border-radius: 8px; "
            f"  margin: 4px; "
            f"}}"
        )
        
        layout = QVBoxLayout(self)
        
        # Header: Name and Module Tag
        header = QHBoxLayout()
        name_lbl = QLabel(metadata.get("name", "Untitled"))
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Colors.FG_PRIMARY}; border: none;")
        
        # Swapped ACCENT for ACCENT_PRIMARY
        mod_lbl = QLabel(metadata.get("module", "").replace("_", " ").upper())
        mod_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; "
            f"font-size: 10px; "
            f"font-weight: bold; "
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; "
            f"border-radius: 4px; "
            f"padding: 2px 4px;"
        )
        
        header.addWidget(name_lbl)
        header.addStretch()
        header.addWidget(mod_lbl)
        layout.addLayout(header)

        # Description
        desc = QLabel(metadata.get("description", "No description provided."))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; border: none;")
        layout.addWidget(desc)

        # Tags - Using FG_SECONDARY for a muted look
        tags = metadata.get("tags", [])
        if tags:
            tag_str = "  ".join([f"#{t}" for t in tags])
            tag_lbl = QLabel(tag_str)
            tag_lbl.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 11px; font-style: italic; border: none;")
            layout.addWidget(tag_lbl)

        # Load Button
        self.btn_load = QPushButton("Open Workflow")
        self.btn_load.setCursor(header.itemAt(0).widget().cursor()) # Just for safety
        self.btn_load.clicked.connect(lambda: on_load_callback(metadata))
        layout.addWidget(self.btn_load)