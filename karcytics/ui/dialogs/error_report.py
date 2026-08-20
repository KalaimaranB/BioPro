"""Premium Error Reporting Dialog for Karcytics."""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from karcytics.core import crash_reporting
from karcytics.ui.theme import Colors, Fonts, theme_manager


class ErrorReportDialog(QDialog):
    """A sleek, theme-aware dialog for displaying system errors and tracebacks."""

    def __init__(self, error_data: dict, parent=None):
        super().__init__(parent)
        self.error_data = error_data
        self.setWindowTitle("System Alert — Karcytics Diagnostic")
        self.setMinimumSize(600, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._setup_ui()
        self._apply_styles()

        from karcytics.ui.theme import theme_manager

        theme_manager.theme_changed.connect(self._apply_styles)

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

        self.subtitle_label = QLabel(f"Source: {self.error_data.get('plugin_id', 'Core System')}")
        self.subtitle_label.setFont(Fonts.CAPTION)

        title_v_layout.addWidget(self.title_label)
        title_v_layout.addWidget(self.subtitle_label)

        header_layout.addWidget(self.icon_label)
        header_layout.addLayout(title_v_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Message
        self.msg_label = QLabel(self.error_data.get("message", "An unexpected error occurred."))
        self.msg_label.setFont(Fonts.BODY)
        self.msg_label.setWordWrap(True)
        layout.addWidget(self.msg_label)

        # Details (Scrollable Traceback)
        self.details_area = QTextEdit()
        self.details_area.setReadOnly(True)
        self.details_area.setPlainText(self.error_data.get("traceback", "No traceback available."))
        mono_font = QFont(Fonts.FAMILY_MONO, 9)
        self.details_area.setFont(mono_font)
        self.details_area.setMinimumHeight(150)
        layout.addWidget(self.details_area)

        # Crash reporting — hidden entirely when no DSN is configured, since
        # there's nothing to send to either way.
        self.send_report_btn = None
        self.consent_checkbox = None
        if crash_reporting.get_configured_dsn() is not None:
            already_auto_sent = bool(self.error_data.get("fatal")) and (
                crash_reporting.is_consent_given() is True
            )

            consent_layout = QHBoxLayout()
            self.consent_checkbox = QCheckBox("Automatically send future crash reports")
            self.consent_checkbox.setChecked(crash_reporting.is_consent_given() is True)
            self.consent_checkbox.toggled.connect(crash_reporting.set_consent)
            consent_layout.addWidget(self.consent_checkbox)

            self.send_report_btn = QPushButton(
                "Report Sent Automatically" if already_auto_sent else "Send This Report"
            )
            self.send_report_btn.setEnabled(not already_auto_sent)
            self.send_report_btn.setToolTip(
                "Sends this error's message and stack trace — file paths are "
                "stripped before anything leaves this machine."
            )
            if not already_auto_sent:
                self.send_report_btn.clicked.connect(self._send_report)
            consent_layout.addWidget(self.send_report_btn)
            consent_layout.addStretch()
            layout.addLayout(consent_layout)

        # Actions
        btn_layout = QHBoxLayout()

        self.log_btn = QPushButton("View Logs")
        self.log_btn.clicked.connect(self._open_log_folder)

        self.copy_btn = QPushButton("Copy Details")
        self.copy_btn.clicked.connect(self._copy_details)

        self.export_btn = QPushButton("Export Diagnostic Pack")
        self.export_btn.clicked.connect(self._export_diagnostic_pack)

        self.contact_label = QLabel("Contact Developer regarding errors")
        self.contact_label.setFont(Fonts.CAPTION)

        self.close_btn = QPushButton("Dismiss")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.log_btn)
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.contact_label)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _apply_styles(self):
        theme_manager.apply_style(self.title_label, f"color: {Colors.ACCENT_DANGER};")
        theme_manager.apply_style(self.subtitle_label, f"color: {Colors.FG_SECONDARY};")
        theme_manager.apply_style(
            self.contact_label, f"color: {Colors.FG_SECONDARY}; margin-right: 10px;"
        )

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
            QTextEdit {{
                background-color: {Colors.BG_DARK};
                color: {Colors.ACCENT_DANGER};
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
        """,
        )

    def _send_report(self):
        """Send this specific report now.

        Sending requires consent (`capture_error_data` no-ops without it),
        so this grants it first if the checkbox isn't already checked —
        clicking "Send This Report" is itself an explicit, informed opt-in,
        disclosed by the button's own tooltip.
        """
        if self.consent_checkbox is not None and not self.consent_checkbox.isChecked():
            self.consent_checkbox.setChecked(True)  # triggers set_consent(True) via toggled

        crash_reporting.capture_error_data(self.error_data)
        assert self.send_report_btn is not None  # only connected when this button exists
        self.send_report_btn.setText("Report Sent — Thank You")
        self.send_report_btn.setEnabled(False)

    def _copy_details(self):
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(json.dumps(self.error_data, indent=4))
        self.copy_btn.setText("Copied!")

    def _open_log_folder(self):
        import os
        import platform
        import subprocess

        log_path = os.path.expanduser("~/.karcytics")
        if os.path.exists(log_path):
            if platform.system() == "Darwin":
                subprocess.run(["open", log_path])
            elif platform.system() == "Windows":
                os.startfile(log_path)
            else:
                import webbrowser

                webbrowser.open(f"file://{log_path}")

    def _export_diagnostic_pack(self):
        import platform

        import psutil
        from PyQt6.QtWidgets import QFileDialog

        from karcytics.core.sbom import SBOMGenerator
        from karcytics.core.utils import AtomicJsonFile

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Diagnostic Pack",
            os.path.expanduser("~/karcytics_diagnostics.json"),
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        pack = {
            "error_report": self.error_data,
            "system_specs": {
                "os": platform.system(),
                "os_release": platform.release(),
                "python": platform.python_version(),
                "cpu_count": psutil.cpu_count(logical=True),
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            },
            "sbom": SBOMGenerator().compile_sbom(),
        }

        try:
            AtomicJsonFile.save(file_path, pack)
            self.export_btn.setText("Pack Exported!")
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to export diagnostic pack: {e}", exc_info=True
            )
            self.export_btn.setText("Export Failed")
