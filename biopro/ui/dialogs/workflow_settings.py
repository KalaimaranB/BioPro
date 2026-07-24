from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from biopro.shared.ui.alerts import ask_question, show_error
from biopro.ui.theme import Colors, theme_manager


class WorkflowSettingsDialog(QDialog):
    """Dialog showing workflow file sizes, tags, and deletion options."""

    workflow_deleted = pyqtSignal()
    attachment_deleted = pyqtSignal()

    def __init__(self, project_manager, module_id: str, filename: str, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.module_id = module_id
        self.filename = filename

        # Load data
        self.payload = self.project_manager.load_workflow_payload(self.filename)
        self.wf_path = self.project_manager.workflows.wf_dir / self.filename
        try:
            from biopro.core.utils import AtomicJsonFile

            self.full_data = AtomicJsonFile.load(self.wf_path, default={})
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(f"Failed to load workflow data: {e}")
            self.full_data = {}

        self.metadata = self.full_data.get("metadata", {})
        self.attachments = self.full_data.get("attachments", [])

        self.setWindowTitle(f"Workflow Settings: {self.metadata.get('name', 'Untitled')}")
        self.setMinimumSize(450, 400)
        theme_manager.apply_style(
            self, f"background-color: {Colors.BG_DARK}; color: {Colors.FG_PRIMARY};"
        )

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        lbl_title = QLabel("Workflow Settings")
        theme_manager.apply_style(
            lbl_title, f"font-size: 18px; font-weight: bold; color: {Colors.FG_PRIMARY};"
        )
        layout.addWidget(lbl_title)

        # Tags
        tags = self.metadata.get("tags", [])
        if tags:
            tag_str = " ".join([f"#{t}" for t in tags])
            lbl_tags = QLabel(f"Tags: {tag_str}")
            theme_manager.apply_style(
                lbl_tags, f"color: {Colors.FG_SECONDARY}; font-style: italic;"
            )
            layout.addWidget(lbl_tags)

        # Main File Section
        layout.addWidget(self._create_section_header("Main Workflow File"))

        wf_size = self.wf_path.stat().st_size if self.wf_path.exists() else 0
        wf_size_str = self._format_size(wf_size)

        main_file_layout = QHBoxLayout()
        lbl_main_name = QLabel(f"{self.filename}")
        lbl_main_size = QLabel(wf_size_str)
        theme_manager.apply_style(lbl_main_size, f"color: {Colors.FG_SECONDARY};")

        main_file_layout.addWidget(lbl_main_name)
        main_file_layout.addStretch()
        main_file_layout.addWidget(lbl_main_size)

        layout.addLayout(main_file_layout)

        # Attachments Section
        if self.attachments:
            layout.addWidget(self._create_section_header("Associated Data (Attachments)"))

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            theme_manager.apply_style(scroll, "QScrollArea { border: none; }")

            att_container = QWidget()
            att_layout = QVBoxLayout(att_container)
            att_layout.setContentsMargins(0, 0, 0, 0)

            for att in self.attachments:
                att_layout.addWidget(self._create_attachment_row(att))

            att_layout.addStretch()
            scroll.setWidget(att_container)
            layout.addWidget(scroll)
        else:
            layout.addWidget(QLabel("No associated data blocks."))

        layout.addStretch()

        # Danger Zone
        danger_frame = QFrame()
        theme_manager.apply_style(
            danger_frame, f"border: 1px solid {Colors.ACCENT_DANGER}; border-radius: 6px;"
        )
        danger_layout = QHBoxLayout(danger_frame)

        lbl_danger = QLabel("Delete Entire Workflow")
        theme_manager.apply_style(
            lbl_danger, "color: {Colors.ACCENT_DANGER}; font-weight: bold; border: none;"
        )

        btn_delete_wf = QPushButton("Delete")
        theme_manager.apply_style(
            btn_delete_wf,
            f"""
            QPushButton {{ background: {Colors.ACCENT_DANGER}44; color: {Colors.ACCENT_DANGER}; border: 1px solid {Colors.ACCENT_DANGER}; border-radius: 4px; padding: 4px 12px; }}
            QPushButton:hover {{ background: {Colors.ACCENT_DANGER}; color: white; }}
        """,
        )
        btn_delete_wf.clicked.connect(self._on_delete_workflow)

        danger_layout.addWidget(lbl_danger)
        danger_layout.addStretch()
        danger_layout.addWidget(btn_delete_wf)

        layout.addWidget(danger_frame)

        # Close
        btn_close = QPushButton("Close")
        theme_manager.apply_style(
            btn_close,
            f"""
            QPushButton {{ background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER}; padding: 6px; border-radius: 4px; }}
            QPushButton:hover {{ background: {Colors.BG_LIGHT}; }}
        """,
        )
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _create_section_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        theme_manager.apply_style(
            lbl,
            f"font-weight: bold; color: {Colors.FG_PRIMARY}; margin-top: 10px; border-bottom: 1px solid {Colors.BORDER};",
        )
        return lbl

    def _create_attachment_row(self, att: dict) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 5, 0, 5)

        name = att.get("filename", "Unknown")
        size = att.get("size_bytes", 0)
        key = att.get("key", "")

        lbl_name = QLabel(name)
        lbl_size = QLabel(self._format_size(size))
        theme_manager.apply_style(lbl_size, f"color: {Colors.FG_SECONDARY};")

        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(24, 24)
        theme_manager.apply_style(
            btn_del,
            f"""
            QPushButton {{ background: transparent; border: none; }}
            QPushButton:hover {{ background: {Colors.ACCENT_DANGER}44; border-radius: 4px; }}
        """,
        )
        btn_del.clicked.connect(lambda: self._on_delete_attachment(key, name))

        row_layout.addWidget(lbl_name)
        row_layout.addStretch()
        row_layout.addWidget(lbl_size)
        row_layout.addWidget(btn_del)

        return row

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def _on_delete_attachment(self, key: str, name: str):
        if ask_question(
            self,
            "Delete Data Block",
            f"Are you sure you want to delete '{name}'?\nThis cannot be undone.",
        ):
            if self.project_manager.delete_workflow_attachment(self.filename, key):
                self.attachment_deleted.emit()
                self.accept()  # Close and let caller refresh
            else:
                show_error(self, "Error", "Failed to delete attachment.")

    def _on_delete_workflow(self):
        if ask_question(
            self,
            "Delete Workflow",
            "Are you sure you want to permanently delete this workflow and all its data?\n\nThis cannot be undone.",
        ):
            if self.project_manager.delete_workflow(self.module_id, self.filename):
                self.workflow_deleted.emit()
                self.accept()
            else:
                show_error(self, "Error", "Failed to delete workflow.")
