"""Premium Error Reporting Dialog for BioPro."""

import os
import json
import webbrowser
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QFrame, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from biopro.ui.theme import Colors, Fonts

class ErrorReportDialog(QDialog):
    """A sleek, theme-aware dialog for displaying system errors and tracebacks."""
    
    def __init__(self, error_data: dict, parent=None):
        super().__init__(parent)
        self.error_data = error_data
        self.setWindowTitle("System Alert — BioPro Diagnostic")
        self.setMinimumSize(600, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.icon_label = QLabel("⚠️")
        self.icon_label.setFont(QFont("Segoe UI Emoji", 32))
        
        title_v_layout = QVBoxLayout()
        self.title_label = QLabel("Something went wrong.")
        self.title_label.setFont(Fonts.H2)
        self.title_label.setStyleSheet(f"color: {Colors.ACCENT_CRITICAL};")
        
        self.subtitle_label = QLabel(f"Source: {self.error_data.get('plugin_id', 'Core System')}")
        self.subtitle_label.setFont(Fonts.CAPTION)
        self.subtitle_label.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
        
        title_v_layout.addWidget(self.title_label)
        title_v_layout.addWidget(self.subtitle_label)
        
        header_layout.addWidget(self.icon_label)
        header_layout.addLayout(title_v_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Message
        self.msg_label = QLabel(self.error_data.get('message', 'An unexpected error occurred.'))
        self.msg_label.setFont(Fonts.BODY)
        self.msg_label.setWordWrap(True)
        layout.addWidget(self.msg_label)

        # Details (Scrollable Traceback)
        self.details_area = QTextEdit()
        self.details_area.setReadOnly(True)
        self.details_area.setPlainText(self.error_data.get('traceback', 'No traceback available.'))
        mono_font = QFont(Fonts.FAMILY_MONO, 9)
        self.details_area.setFont(mono_font)
        self.details_area.setMinimumHeight(150)
        layout.addWidget(self.details_area)

        # Actions
        btn_layout = QHBoxLayout()
        
        self.log_btn = QPushButton("View Logs")
        self.log_btn.clicked.connect(self._open_log_folder)
        
        self.copy_btn = QPushButton("Copy Details")
        self.copy_btn.clicked.connect(self._copy_details)
        
        self.contact_label = QLabel("Contact Developer regarding errors")
        self.contact_label.setFont(Fonts.CAPTION)
        self.contact_label.setStyleSheet(f"color: {Colors.FG_SECONDARY}; margin-right: 10px;")
        
        self.close_btn = QPushButton("Dismiss")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.log_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.contact_label)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_DARKER};
                border: 1px solid {Colors.BORDER_LIGHT};
            }}
            QLabel {{
                color: {Colors.FG_PRIMARY};
            }}
            QTextEdit {{
                background-color: {Colors.BG_DARKEST};
                color: {Colors.ACCENT_CRITICAL};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton {{
                background-color: {Colors.BG_DARKEST};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER_LIGHT};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_LIGHT};
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)

    def _copy_details(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(json.dumps(self.error_data, indent=4))
        self.copy_btn.setText("Copied!")

    def _open_log_folder(self):
        import platform
        import subprocess
        import os
        log_path = os.path.expanduser("~/.biopro")
        if os.path.exists(log_path):
            if platform.system() == "Darwin":
                subprocess.run(["open", log_path])
            elif platform.system() == "Windows":
                os.startfile(log_path)
            else:
                import webbrowser
                webbrowser.open(f"file://{log_path}")
