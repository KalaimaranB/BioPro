"""Simple text window for viewing application logs."""

from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from biopro.ui.theme import Colors, Fonts


class LogViewerDialog(QDialog):
    """A dialog to display the contents of the current biopro.log file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BioPro Logs")
        self.setMinimumSize(800, 600)

        self._setup_ui()
        self._apply_styles()
        self._load_logs()

        from biopro.ui.theme import theme_manager

        theme_manager.theme_changed.connect(self._apply_styles)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        mono_font = QFont(Fonts.FAMILY_MONO, 10)
        self.text_area.setFont(mono_font)
        self.text_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.text_area)

        btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self._copy_logs)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_logs)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
            }}
            QTextEdit {{
                background-color: {Colors.BG_DARK};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 10px;
            }}
            QPushButton {{
                background-color: {Colors.BG_DARK};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_MEDIUM};
                border: 1px solid {Colors.ACCENT_PRIMARY};
            }}
        """)

    def _load_logs(self):
        log_file = Path.home() / ".biopro" / "biopro.log"
        if log_file.exists():
            try:
                with open(log_file, encoding="utf-8") as f:
                    content = f.read()
                self.text_area.setPlainText(content)
                # Scroll to bottom
                scrollbar = self.text_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            except Exception as e:
                self.text_area.setPlainText(f"Error reading log file:\n{e}")
        else:
            self.text_area.setPlainText("Log file not found at ~/.biopro/biopro.log")
        self.copy_btn.setText("Copy to Clipboard")

    def _copy_logs(self):
        QApplication.clipboard().setText(self.text_area.toPlainText())
        self.copy_btn.setText("Copied!")
