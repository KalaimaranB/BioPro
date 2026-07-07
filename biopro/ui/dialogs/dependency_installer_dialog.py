import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from biopro.core.package_manager import PluginInstallerWorker

logger = logging.getLogger(__name__)


class DependencyInstallerDialog(QDialog):
    """Dialog that shows progress while installing python dependencies for a plugin."""

    def __init__(self, plugin_dir: Path, plugin_name: str, parent=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.plugin_name = plugin_name

        self.setWindowTitle(f"Installing Dependencies - {self.plugin_name}")
        self.setFixedSize(400, 150)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        # Prevent closing during install
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.setup_ui()
        self.start_installation()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.info_label = QLabel(f"Setting up Python environment for {self.plugin_name}...")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Starting installation...")
        layout.addWidget(self.status_label)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.hide()
        self.retry_btn.clicked.connect(self.start_installation)
        btn_layout.addWidget(self.retry_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.hide()
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def start_installation(self):
        self.retry_btn.hide()
        self.close_btn.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Installing...")

        self.worker = PluginInstallerWorker(self.plugin_dir)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, value):
        self.progress_bar.setValue(value)

    def on_finished(self, success: bool, message: str):
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Installation complete!")
            self.accept()
        else:
            self.status_label.setText(f"Error: {message}")
            self.retry_btn.show()
            self.close_btn.show()
            # Re-enable close button on failure
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)
            self.show()
