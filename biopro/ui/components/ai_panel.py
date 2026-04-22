"""AI Chat Interface Floating Window."""

from pathlib import Path
import urllib.request
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QCheckBox, QWidget, QScrollArea, QProgressBar,
    QSizePolicy
)
from biopro.ui.theme import Colors, Fonts
from biopro.sdk.core.ai import ai_manager, AIAssistant
from biopro.core.task_scheduler import TaskScheduler
from biopro.sdk.core.managed_task import FunctionalTask

from PyQt6.QtWidgets import QDialog, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout, QLabel

class SoulEditorDialog(QDialog):
    """A built-in editor for the AI's personality (soul.md)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit AI Personality (Soul)")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel("Describe how you want your AI to behave:")
        self.label.setStyleSheet(f"font-weight: bold; color: {Colors.ACCENT_PRIMARY};")
        layout.addWidget(self.label)
        
        self.editor = QTextEdit()
        self.editor.setStyleSheet(f"background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; padding: 8px;")
        layout.addWidget(self.editor)
        
        # Load current content
        self.soul_path = Path.home() / ".biopro" / "soul.md"
        if self.soul_path.exists():
            self.editor.setPlainText(self.soul_path.read_text())
        else:
            self.editor.setPlainText("# BioPro AI Soul\n- Be a helpful assistant.")

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.setStyleSheet(f"background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; font-weight: bold; padding: 8px;")
        self.btn_save.clicked.connect(self._save)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def _save(self):
        try:
            self.soul_path.parent.mkdir(parents=True, exist_ok=True)
            self.soul_path.write_text(self.editor.toPlainText())
            self.accept()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", f"Could not save personality: {e}")

class AIChatWindow(QDialog):
    """Floating window for AI Interaction."""
    
    def __init__(self, parent=None, current_module_id: str = None):
        # We use a tool window so it floats but stays on top of the parent
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Gemma 4 Assistant")
        self.setMinimumSize(400, 600)
        self.current_module_id = current_module_id
        self.assistant = AIAssistant()
        
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self._setup_ui()
        self._connect_signals()
        
        self._check_server_state()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header / Status
        self.header_layout = QHBoxLayout()
        self.status_lbl = QLabel("🧠 AI Assistant")
        self.status_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: bold;")
        self.header_layout.addWidget(self.status_lbl)
        
        self.thinking_indicator = QLabel("Thinking...")
        self.thinking_indicator.setStyleSheet(f"color: {Colors.ACCENT_PRIMARY}; font-style: italic;")
        self.thinking_indicator.hide()
        self.header_layout.addWidget(self.thinking_indicator)
        self.header_layout.addStretch()
        
        self.btn_soul = QPushButton("⚙️ Personality")
        self.btn_soul.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.FG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
            }}
        """)
        self.header_layout.addWidget(self.btn_soul)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.ACCENT_PRIMARY};
                border: 1px solid {Colors.ACCENT_PRIMARY};
                border-radius: 4px;
                padding: 2px 8px;
            }}
            QPushButton:hover {{
                background: {Colors.ACCENT_PRIMARY};
                color: white;
            }}
        """)
        self.header_layout.addWidget(self.btn_clear)
        
        layout.addLayout(self.header_layout)
        
        # Context Checklist
        self.context_group = QWidget()
        ctx_layout = QHBoxLayout(self.context_group)
        ctx_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chk_module = QCheckBox("Active Module Context")
        # Default to checking module context if we are in one
        self.chk_module.setChecked(self.current_module_id is not None)
        self.chk_module.setEnabled(self.current_module_id is not None)
        ctx_layout.addWidget(self.chk_module)
        
        self.chk_core = QCheckBox("Core BioPro Context")
        # Default to core context if we are NOT in a module
        self.chk_core.setChecked(self.current_module_id is None)
        ctx_layout.addWidget(self.chk_core)
        ctx_layout.addStretch()
        layout.addWidget(self.context_group)
        
        # Download / Setup UI (hidden by default)
        self.setup_widget = QWidget()
        setup_layout = QVBoxLayout(self.setup_widget)
        self.setup_msg = QLabel("Gemma 4 model is missing.")
        self.btn_download = QPushButton("Download Gemma 4")
        self.btn_download.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; "
            f"border-radius: 4px; padding: 8px; font-weight: bold; }}"
        )
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        
        setup_layout.addWidget(self.setup_msg)
        setup_layout.addWidget(self.btn_download)
        setup_layout.addWidget(self.progress_bar)
        setup_layout.addStretch()
        self.setup_widget.hide()
        layout.addWidget(self.setup_widget)
        
        # Chat UI
        self.chat_widget = QWidget()
        chat_layout = QVBoxLayout(self.chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet(f"background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 8px;")
        chat_layout.addWidget(self.chat_history)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question...")
        self.btn_send = QPushButton("Send")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)
        chat_layout.addLayout(input_layout)
        
        layout.addWidget(self.chat_widget)
        
    def _connect_signals(self):
        ai_manager.signals.prompt_download.connect(self._show_download_ui)
        ai_manager.signals.server_started.connect(self._show_chat_ui)
        ai_manager.signals.download_progress.connect(self.progress_bar.setValue)
        ai_manager.signals.server_error.connect(self._on_server_error)
        
        self.btn_send.clicked.connect(self._send_message)
        self.input_field.returnPressed.connect(self._send_message)
        self.btn_download.clicked.connect(self._start_download)
        self.btn_clear.clicked.connect(self._clear_chat)
        self.btn_soul.clicked.connect(self._edit_soul)
        
    def _edit_soul(self):
        """Open the built-in editor for the AI personality."""
        dialog = SoulEditorDialog(self)
        if dialog.exec():
            # Personality was updated and saved to ~/.biopro/soul.md
            self._append_chat("*System: AI Personality updated successfully.*")
        
    def _clear_chat(self):
        self.chat_history.clear()
        self.assistant.history = []
        self._append_chat("<i>Conversation cleared.</i>")

    def _check_server_state(self):
        if ai_manager.is_running():
            self._show_chat_ui()
        else:
            self.status_lbl.setText("🚀 Launching Engine...")
            ai_manager.start_server()
            
    def _show_download_ui(self):
        self.chat_widget.hide()
        self.context_group.hide()
        self.setup_widget.show()
        
    def _show_chat_ui(self):
        self.status_lbl.setText("🧠 AI Assistant")
        self.setup_widget.hide()
        self.context_group.show()
        self.chat_widget.show()
        self.update_module_context(self.current_module_id)

    def update_module_context(self, module_id: str):
        """Update the module context checkbox based on current active module."""
        self.current_module_id = module_id
        if module_id:
            self.chk_module.setEnabled(True)
            self.chk_module.setText(f"Active Module Context ({module_id})")
            self.chk_module.setChecked(True)
            self.chk_core.setChecked(False)
        else:
            self.chk_module.setEnabled(False)
            self.chk_module.setText("Active Module Context (None)")
            self.chk_module.setChecked(False)
            self.chk_core.setChecked(True)

    def _start_download(self):
        """Starts a real background download for the Gemma model."""
        try:
            self.btn_download.setEnabled(False)
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self.setup_msg.setText("Initializing download...")
            
            # Using a small Gemma-2B quantized model as the "Gemma 4" implementation
            url = "https://huggingface.co/lmstudio-community/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf?download=true"
            dest = Path(ai_manager.model_path)
            
            # Ensure the directory is writable and exists. Use absolute path to avoid CWD issues.
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Test write permissions
                test_file = dest.parent / ".write_test"
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                raise Exception(f"Permission denied: Cannot write to {dest.parent}. {e}")
            
            self.setup_msg.setText(f"Downloading model to persistent storage...")
            self.downloader = DownloadThread(url, str(dest))
            self.downloader.progress.connect(self.progress_bar.setValue)
            self.downloader.finished.connect(self._on_download_finished)
            self.downloader.error.connect(self._on_download_error)
            self.downloader.start()
        except Exception as e:
            self._on_download_error(str(e))

    def _on_download_finished(self):
        self.setup_msg.setText("Download Complete! Initializing AI Engine...")
        # Small delay to let the user see the "Complete" message
        QTimer.singleShot(1500, self._finalize_setup)

    def _finalize_setup(self):
        ai_manager.start_server()
        self._show_chat_ui()

    def _on_download_error(self, error_msg):
        self.btn_download.setEnabled(True)
        self.setup_msg.setText(f"Download Failed: {error_msg}")
        self.progress_bar.hide()

    def _on_server_error(self, error_msg):
        """Handle AI Engine crashes or startup failures."""
        self.thinking_indicator.hide()
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self._append_chat(f"<span style='color:red;'>**System Error:** {error_msg}</span>")
        self.status_lbl.setText("🧠 AI Assistant (Offline)")

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        self.input_field.clear()
        self._append_chat(f"**You:** {text}")
        
        # Prepare context options
        include_module = self.chk_module.isChecked()
        include_core = self.chk_core.isChecked()
        
        self.thinking_indicator.show()
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Use FunctionalTask to run the AI query in the background so UI doesn't freeze
        task = FunctionalTask(
            lambda: self.assistant.ask_question(
                prompt=text, 
                plugin_id=self.current_module_id if include_module else None,
                include_core=include_core
            ),
            name="AIAssistantQuery"
        )
        
        # Import TaskScheduler locally if not global
        from biopro.core.task_scheduler import task_scheduler
        worker = task_scheduler.submit(task)
        worker.finished.connect(self._on_ai_response)
        worker.error.connect(self._on_ai_error)
    def _on_ai_response(self, result: dict):
        self.thinking_indicator.hide()
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        
        reply = result.get("result", "Error parsing response.")
        
        # Build context summary label
        ctx_parts = []
        if self.chk_module.isChecked() and self.current_module_id:
            ctx_parts.append(f"[{self.current_module_id}]")
        if self.chk_core.isChecked():
            ctx_parts.append("[Core]")
            
        ctx_summary = f"*Context active: {' '.join(ctx_parts)}*" if ctx_parts else ""
        
        full_msg = f"### Gemma 4\n{ctx_summary}\n\n{reply}"
        self._append_chat(full_msg)
        
    def _on_ai_error(self, error: str):
        self.thinking_indicator.hide()
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self._append_chat(f"<span style='color:red;'>**Error:** {error}</span>")
        
    def _append_chat(self, text: str):
        """Append text to chat history with markdown rendering support."""
        from PyQt6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setMarkdown(text)
        
        # Append as HTML to preserve the markdown formatting
        self.chat_history.append(doc.toHtml())
        
        # Ensure the scrollbar follows
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, url, dest):
        super().__init__()
        self.url = url
        self.dest = dest

    def run(self):
        try:
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    prog = int(count * block_size * 100 / total_size)
                    self.progress.emit(min(prog, 100))

            urllib.request.urlretrieve(self.url, self.dest, reporthook=report_hook)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
