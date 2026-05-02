"""AI Chat Interface Floating Window (SOLID Refactored)."""

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QCheckBox, QWidget, QScrollArea, QProgressBar,
    QSizePolicy
)
from biopro.ui.theme import Colors, Fonts, theme_manager
from biopro.sdk.core.ai import ai_manager
from biopro.core.sound_manager import sound_manager
from biopro.ui.ai.service import AIService
from biopro.ui.ai.context_panel import ContextPanel
import logging

logger = logging.getLogger(__name__)

class AIChatWindow(QDialog):
    """Floating window for AI Interaction."""
    
    def __init__(self, parent=None, current_module_id: str = None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("BioPro AI Assistant")
        self.setMinimumSize(800, 700)
        self.current_module_id = current_module_id
        
        # Logic Service
        self.service = AIService()
        
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self._setup_ui()
        self._connect_signals()
        self._check_server_state()

        theme_manager.theme_changed.connect(self._apply_theme_styles)
        self._apply_theme_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header / Status
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 10)
        self.header_layout.setSpacing(10)
        
        self.status_lbl = QLabel("🧠 AI Assistant")
        self.status_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: bold;")
        self.header_layout.addWidget(self.status_lbl)
        self.header_layout.addStretch()

        self.btn_ctx_toggle = QPushButton("📂 Context")
        self.btn_ctx_toggle.setCheckable(True)
        self.btn_ctx_toggle.setChecked(True)
        self.btn_ctx_toggle.setFixedHeight(28)
        self.btn_ctx_toggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.ACCENT_PRIMARY}; border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; padding: 2px 10px; font-size: 11px; }}
            QPushButton:checked {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; }}
        """)
        self.header_layout.addWidget(self.btn_ctx_toggle)

        self.btn_soul = QPushButton("⚙️")
        self.btn_soul.setFixedHeight(28)
        self.btn_soul.setStyleSheet(f"background: transparent; color: {Colors.FG_SECONDARY}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 2px 8px;")
        self.header_layout.addWidget(self.btn_soul)

        self.btn_power = QPushButton("⭕ OFF")
        self.btn_power.setCheckable(True)
        self.btn_power.setFixedHeight(28)
        self.btn_power.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.FG_SECONDARY}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 2px 10px; }}
            QPushButton:checked {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; border: none; font-weight: bold; }}
        """)
        self.header_layout.addWidget(self.btn_power)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedHeight(28)
        self.btn_clear.setStyleSheet(f"QPushButton {{ background: transparent; color: {Colors.ACCENT_PRIMARY}; border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; padding: 2px 10px; }}")
        self.header_layout.addWidget(self.btn_clear)

        layout.addLayout(self.header_layout)

        # Main Content Area
        self.main_content = QWidget()
        self.content_layout = QHBoxLayout(self.main_content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        
        # LEFT: Chat Area
        self.chat_area = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_area)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet(f"background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 8px; padding: 10px; font-size: 13px;")
        self.chat_layout.addWidget(self.chat_history)

        self.thinking_indicator = QLabel("<i>The Assistant is thinking...</i>")
        self.thinking_indicator.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 11px; margin-left: 5px;")
        self.thinking_indicator.hide()
        self.chat_layout.addWidget(self.thinking_indicator)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question...")
        self.btn_send = QPushButton("Send")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)
        self.chat_layout.addLayout(input_layout)
        
        self.content_layout.addWidget(self.chat_area, 2)
        
        # RIGHT: Context Sidebar
        self.context_sidebar = ContextPanel(self, self.service.assistant)
        self.context_sidebar.setFixedWidth(350)
        self.context_sidebar.setStyleSheet(f"background: {Colors.BG_DARK}; border-left: 1px solid {Colors.BORDER};")
        self.content_layout.addWidget(self.context_sidebar)
        
        layout.addWidget(self.main_content)

        # Config Checkboxes (Under Header)
        self.context_widget = QWidget()
        ctx_opts = QHBoxLayout(self.context_widget)
        ctx_opts.setContentsMargins(0, 0, 0, 5)
        self.chk_module = QCheckBox("Module (None)")
        self.chk_module.setChecked(True)
        self.chk_module.setEnabled(False)
        self.chk_core = QCheckBox("Core Docs")
        self.chk_core.setChecked(True)
        ctx_opts.addWidget(self.chk_module)
        ctx_opts.addWidget(self.chk_core)
        ctx_opts.addStretch()
        layout.insertWidget(1, self.context_widget)

        # Setup / Download UI
        self.setup_widget = QWidget()
        setup_layout = QVBoxLayout(self.setup_widget)
        self.setup_msg = QLabel("AI model is missing.")
        self.btn_download = QPushButton("Download Gemma Model")
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        setup_layout.addWidget(self.setup_msg)
        setup_layout.addWidget(self.btn_download)
        setup_layout.addWidget(self.progress_bar)
        self.setup_widget.hide()
        layout.addWidget(self.setup_widget)

    def _apply_theme_styles(self):
        """Update window colors and sub-components when theme changes."""
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        self.status_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: bold; color: {Colors.FG_PRIMARY};")
        self.chat_history.setStyleSheet(f"background: {Colors.BG_DARK}; border: 1px solid {Colors.BORDER}; border-radius: 8px; padding: 10px; font-size: 13px; color: {Colors.FG_PRIMARY};")
        self.thinking_indicator.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 11px; margin-left: 5px;")
        self.context_sidebar.setStyleSheet(f"background: {Colors.BG_DARK}; border-left: 1px solid {Colors.BORDER};")
        
        self.btn_ctx_toggle.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.ACCENT_PRIMARY}; border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; padding: 2px 10px; font-size: 11px; }}
            QPushButton:checked {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; }}
        """)
        self.btn_soul.setStyleSheet(f"background: transparent; color: {Colors.FG_SECONDARY}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 2px 8px;")
        self.btn_power.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {Colors.FG_SECONDARY}; border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 2px 10px; }}
            QPushButton:checked {{ background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST}; border: none; font-weight: bold; }}
        """)
        self.btn_clear.setStyleSheet(f"QPushButton {{ background: transparent; color: {Colors.ACCENT_PRIMARY}; border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px; padding: 2px 10px; }}")
        
        # Refresh any SDK buttons or custom widgets inside
        for widget in self.findChildren(QWidget):
            if hasattr(widget, "_apply_theme_styles") and widget is not self:
                widget._apply_theme_styles()
            elif hasattr(widget, "refresh_styles"):
                widget.refresh_styles()

    def _connect_signals(self):
        ai_manager.signals.prompt_download.connect(self._show_download_ui)
        ai_manager.signals.server_started.connect(self._show_chat_ui)
        ai_manager.signals.download_progress.connect(self.progress_bar.setValue)
        ai_manager.signals.server_error.connect(self._on_server_error)
        
        self.btn_ctx_toggle.clicked.connect(self._toggle_context_sidebar)
        self.chk_module.stateChanged.connect(self._on_context_type_changed)
        self.chk_core.stateChanged.connect(self._on_context_type_changed)
        self.context_sidebar.selection_changed.connect(self._on_context_selection_changed)

        self.btn_send.clicked.connect(self._send_message)
        self.input_field.returnPressed.connect(self._send_message)
        self.btn_download.clicked.connect(self._start_download)
        self.btn_clear.clicked.connect(self._clear_chat)
        self.btn_soul.clicked.connect(self._edit_soul)
        self.btn_power.clicked.connect(self._toggle_server)

    def _toggle_context_sidebar(self):
        show = self.btn_ctx_toggle.isChecked()
        self.context_sidebar.setVisible(show)
        self.setMinimumWidth(700 if show else 500)
        if not show: self.resize(400, self.height())

    def _on_context_type_changed(self):
        self.context_sidebar.refresh(
            self.current_module_id if self.chk_module.isChecked() else None,
            self.chk_core.isChecked()
        )

    def _on_context_selection_changed(self, selected_files):
        self.service.selected_context_files = selected_files

    def _send_message(self):
        text = self.input_field.text().strip()
        logger.info(f"AI Message Send clicked. Text length: {len(text)}")
        
        if not text: return
        self.input_field.clear()
        
        self.service.full_chat_md += f"\n\n**You:** {text}\n\n"
        self._render_chat()
        
        self.thinking_indicator.show()
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)
        
        personality_prefix = ""
        if "Star Wars" in theme_manager.current_theme_name:
            personality_prefix = "SYSTEM NOTICE: Adopt the personality of a helpful, analytical Droid. "
            sound_manager.play_beep()

        self.service.full_chat_md += "**Assistant:** "
        self.ai_thread = self.service.get_streaming_thread(
            personality_prefix + text,
            self.current_module_id if self.chk_module.isChecked() else None,
            self.chk_core.isChecked()
        )
        self.ai_thread.chunk_received.connect(self._on_ai_chunk)
        self.ai_thread.finished.connect(self._on_ai_finished)
        self.ai_thread.error.connect(self._on_server_error)
        self.ai_thread.start()

    def _on_ai_chunk(self, chunk):
        self.thinking_indicator.hide()
        self.service.full_chat_md += chunk
        self._render_chat()

    def _on_ai_finished(self, result):
        self.thinking_indicator.hide()
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        
        sources = result.get("sources", [])
        if sources:
            self.service.full_chat_md += f"\n\n*Sources: {', '.join(sources)}*"
            self._render_chat()

    def _render_chat(self):
        self.chat_history.setMarkdown(self.service.full_chat_md)
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def _clear_chat(self):
        self.service.clear_history()
        self._render_chat()

    def _toggle_server(self):
        enabled = self.btn_power.isChecked()
        self.btn_power.setText("🟢 ON" if enabled else "⭕ OFF")
        if enabled: self._check_server_state()
        else:
            ai_manager.stop_server()
            self.service.full_chat_md += "\n\n*System: AI Server manually disabled.*\n\n"
            self._render_chat()
            self.status_lbl.setText("🧠 AI Assistant (Offline)")

    def _check_server_state(self):
        if ai_manager.is_running(): self._show_chat_ui()
        else:
            self.status_lbl.setText("🚀 Launching Engine...")
            ai_manager.start_server()

    def _show_download_ui(self):
        self.main_content.hide()
        self.context_widget.hide()
        self.setup_widget.show()

    def _show_chat_ui(self):
        self.status_lbl.setText("🧠 AI Assistant")
        self.setup_widget.hide()
        self.main_content.show()
        self.context_widget.show()
        self.update_module_context(self.current_module_id)

    def update_module_context(self, module_id: str):
        self.current_module_id = module_id
        if module_id:
            self.chk_module.setEnabled(True)
            self.chk_module.setText(f"Module ({module_id})")
        self.context_sidebar.refresh(module_id, self.chk_core.isChecked())

    def _start_download(self):
        self.btn_download.setEnabled(False)
        self.progress_bar.show()
        ai_manager.download_model()

    def _on_server_error(self, error):
        self.service.full_chat_md += f"\n\n**Error:** {error}\n\n"
        self._render_chat()
        self.thinking_indicator.hide()
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)

    def _edit_soul(self):
        dialog = SoulEditorDialog(self)
        if dialog.exec():
            self.service.full_chat_md += "\n\n*System: AI Personality updated successfully.*\n\n"
            self._render_chat()

class SoulEditorDialog(QDialog):
    """Simple internal editor for AI personality."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit AI Personality")
        self.setMinimumSize(400, 300)
        self.soul_path = Path.home() / ".biopro" / "soul.md"
        
        layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        content = self.soul_path.read_text() if self.soul_path.exists() else "# AI Personality\n\nBe a helpful assistant."
        self.editor.setPlainText(content)
        layout.addWidget(self.editor)
        
        btns = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        layout.addLayout(btns)

    def _save(self):
        self.soul_path.parent.mkdir(parents=True, exist_ok=True)
        self.soul_path.write_text(self.editor.toPlainText())
        self.accept()
