"""Diagnostics & Privacy settings dialog."""

import json

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from karcytics.core import crash_reporting
from karcytics.core.config import AppConfig
from karcytics.core.diagnostics import diagnostics
from karcytics.ui.theme import Colors, Fonts, theme_manager


class DiagnosticsSettingsDialog(QDialog):
    """Lets the user control crash reporting consent and inspect diagnostic data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diagnostics & Privacy")
        self.setMinimumSize(480, 320)

        self._setup_ui()
        self._apply_styles()

        theme_manager.theme_changed.connect(self._apply_styles)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.title_label = QLabel("Diagnostics & Privacy")
        self.title_label.setFont(Fonts.H2)
        layout.addWidget(self.title_label)

        dsn_configured = crash_reporting.get_configured_dsn() is not None

        self.consent_checkbox = QCheckBox("Automatically send crash reports to help fix issues")
        self.consent_checkbox.setChecked(crash_reporting.is_consent_given() is True)
        self.consent_checkbox.setEnabled(dsn_configured)
        self.consent_checkbox.toggled.connect(crash_reporting.set_consent)
        layout.addWidget(self.consent_checkbox)

        self.detail_label = QLabel(
            "Crash reports include the error message, stack trace, and OS/app "
            "version — file paths are stripped before anything leaves this machine."
            if dsn_configured
            else "Crash reporting isn't configured for this build."
        )
        self.detail_label.setFont(Fonts.CAPTION)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()

        self.open_logs_btn = QPushButton("Open Logs Folder")
        self.open_logs_btn.clicked.connect(self._open_logs_folder)
        btn_layout.addWidget(self.open_logs_btn)

        self.copy_report_btn = QPushButton("Copy Diagnostic Report")
        self.copy_report_btn.clicked.connect(self._copy_diagnostic_report)
        btn_layout.addWidget(self.copy_report_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _apply_styles(self):
        theme_manager.apply_style(self.title_label, f"color: {Colors.FG_PRIMARY};")
        theme_manager.apply_style(self.detail_label, f"color: {Colors.FG_SECONDARY};")
        theme_manager.apply_style(
            self,
            f"""
            QDialog {{
                background-color: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
            }}
            QLabel {{
                color: {Colors.FG_PRIMARY};
            }}
            QCheckBox {{
                color: {Colors.FG_PRIMARY};
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
        """,
        )

    def _open_logs_folder(self):
        logs_dir = AppConfig.APP_DATA_DIR / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs_dir)))

    def _copy_diagnostic_report(self):
        report = diagnostics.get_full_diagnostic_report()
        QApplication.clipboard().setText(json.dumps(report, indent=2, default=str))
        self.copy_report_btn.setText("Copied!")
