from PyQt6.QtWidgets import QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt
from biopro.ui.theme import Colors, Fonts # Assuming these exist in your theme file

class PrimaryButton(QPushButton):
    """The main action button (Green/Accent color)."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_SECONDARY}; }}
        """)

class SecondaryButton(QPushButton):
    """The standard outline/cancel button."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Colors.BG_LIGHT}; }}
        """)

class ModuleCard(QFrame):
    """A standardized, interactive card for lists and grids."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BioCard")
        self.setStyleSheet(f"""
            QFrame#BioCard {{
                background-color: {Colors.BG_DARK}; 
                border: 1px solid {Colors.BORDER}; 
                border-radius: 10px;
            }}
            QFrame#BioCard:hover {{
                border: 1px solid {Colors.ACCENT_PRIMARY};
                background-color: {Colors.BG_MEDIUM};
            }}
        """)

class HeaderLabel(QLabel):
    """Standardized H1 Header."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: bold; color: {Colors.FG_PRIMARY};")
        

class DangerButton(QPushButton):
    """The standard destructive/remove button."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc3545; 
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #c82333; }}
        """)