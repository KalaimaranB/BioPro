"""Reusable UI Cards for BioPro."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from biopro.ui.theme import Colors, Fonts

class ModuleCard(QFrame):
    """Clickable card representing one analysis module."""
    clicked = pyqtSignal()

    def __init__(self, icon: str, title: str, description: str, badge: str = "", enabled: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._enabled = enabled
        self.setObjectName("moduleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setMinimumSize(220, 150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()

        if badge:
            badge_lbl = QLabel(badge)
            badge_lbl.setStyleSheet(f"background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 700;")
            top_row.addWidget(badge_lbl)
        elif not enabled:
            soon_lbl = QLabel("Coming soon")
            soon_lbl.setStyleSheet(f"background: {Colors.BG_LIGHT}; color: {Colors.FG_DISABLED}; border-radius: 5px; padding: 2px 7px; font-size: 10px; font-weight: 600;")
            top_row.addWidget(soon_lbl)

        layout.addLayout(top_row)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 700; color: {'#e6edf3' if enabled else Colors.FG_DISABLED}; background: transparent;")
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_SMALL}px; color: {Colors.FG_SECONDARY}; background: transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        layout.addStretch()
        self._apply_style(False)

    def _apply_style(self, hovered: bool) -> None:
        if not self._enabled:
            self.setStyleSheet(f"QFrame#moduleCard {{ background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 10px; }}")
            return
        border = Colors.ACCENT_PRIMARY if hovered else Colors.BORDER
        bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
        self.setStyleSheet(f"QFrame#moduleCard {{ background: {bg}; border: 1.5px solid {border}; border-radius: 10px; }}")

    def enterEvent(self, event) -> None:
        if self._enabled: self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._enabled: self.clicked.emit()
        super().mousePressEvent(event)


class DashboardWorkflowCard(QFrame):
    """Clickable card representing a saved workflow with a delete button."""
    clicked = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, title: str, date_str: str, module_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workflowCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(220, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Top row: Module Name and Trash Button
        top_row = QHBoxLayout()
        mod_lbl = QLabel(module_name)
        mod_lbl.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {Colors.ACCENT_PRIMARY}; background: transparent; text-transform: uppercase;")
        top_row.addWidget(mod_lbl)
        top_row.addStretch()

        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; font-size: 12px; }}
            QPushButton:hover {{ background: {Colors.ACCENT_DANGER}44; border: 1px solid {Colors.ACCENT_DANGER}; }}
        """)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        top_row.addWidget(self.btn_delete)
        layout.addLayout(top_row)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 700; color: #e6edf3; background: transparent;")
        layout.addWidget(title_lbl)

        date_lbl = QLabel(f"Saved: {date_str}")
        date_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; background: transparent;")
        layout.addWidget(date_lbl)

        layout.addStretch()
        self._apply_style(False)

    def _on_delete_clicked(self) -> None:
        self.delete_requested.emit()

    def _apply_style(self, hovered: bool) -> None:
        border = Colors.FG_SECONDARY if hovered else Colors.BORDER
        bg = Colors.BG_MEDIUM if hovered else Colors.BG_DARK
        self.setStyleSheet(f"QFrame#workflowCard {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; }}")

    def enterEvent(self, event) -> None:
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if not self.btn_delete.geometry().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mousePressEvent(event)


class DetailedWorkflowCard(QFrame):
    """A visual card representing a saved workflow with tags and load button."""
    def __init__(self, metadata: dict, on_load_callback):
        super().__init__()
        self.metadata = metadata
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
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

        # Tags
        tags = metadata.get("tags", [])
        if tags:
            tag_str = "  ".join([f"#{t}" for t in tags])
            tag_lbl = QLabel(tag_str)
            tag_lbl.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 11px; font-style: italic; border: none;")
            layout.addWidget(tag_lbl)

        # Load Button
        self.btn_load = QPushButton("Open Workflow")
        self.btn_load.setCursor(header.itemAt(0).widget().cursor()) # Safety for cursor
        self.btn_load.clicked.connect(lambda: on_load_callback(metadata))
        layout.addWidget(self.btn_load)
