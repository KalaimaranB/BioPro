import pytest
from PyQt6.QtCore import Qt
from biopro.ui.components.ai_panel import AIChatWindow

def test_ai_chat_window_initialization(qtbot):
    """Ensure the AI Chat Window initializes and has all required methods."""
    window = AIChatWindow()
    qtbot.addWidget(window)
    
    # Check that methods exist (this would catch the AttributeError)
    assert hasattr(window, '_send_message')
    assert hasattr(window, '_on_ai_response')
    assert hasattr(window, '_on_ai_error')
    assert hasattr(window, '_append_chat')
    
    assert window.windowTitle() == "Gemma 4 Assistant"

def test_ai_chat_window_ui_elements(qtbot):
    """Check that UI elements are present."""
    window = AIChatWindow()
    qtbot.addWidget(window)
    
    assert window.input_field is not None
    assert window.btn_send is not None
    assert window.chat_history is not None
    assert window.thinking_indicator is not None

def test_ai_chat_window_send_message(qtbot, monkeypatch):
    """Test that sending a message triggers the scheduler correctly."""
    window = AIChatWindow()
    qtbot.addWidget(window)
    
    # Mock the scheduler so we don't actually run threads
    class MockWorker:
        class MockSignal:
            def connect(self, slot): pass
        finished = MockSignal()
        error = MockSignal()

    def mock_submit(task, state=None):
        return MockWorker()

    from biopro.core.task_scheduler import task_scheduler
    monkeypatch.setattr(task_scheduler, "submit", mock_submit)
    
    window.input_field.setText("Tell me a joke")
    qtbot.mouseClick(window.btn_send, Qt.MouseButton.LeftButton)
    
    # If this doesn't raise TypeError/AttributeError, we are good
    assert window.input_field.text() == ""
    assert "You: Tell me a joke" in window.chat_history.toPlainText()

def test_download_crash_prevention(qtbot, monkeypatch):
    """Verify that AIChatWindow handles permission errors during download start without crashing."""
    window = AIChatWindow()
    qtbot.addWidget(window)
    
    # Mock Path.mkdir to raise PermissionError
    def mock_mkdir(self, **kwargs):
        raise PermissionError("Access denied")
    
    monkeypatch.setattr("pathlib.Path.mkdir", mock_mkdir)
    
    # Start download
    window._start_download()
    
    # Verify that the error was caught and displayed instead of crashing
    assert "Permission denied" in window.setup_msg.text()
    assert window.btn_download.isEnabled() # Re-enabled on error

def test_download_write_test_failure(qtbot, monkeypatch):
    """Verify that the write test prevents starting a download that would fail later."""
    window = AIChatWindow()
    qtbot.addWidget(window)
    
    # Mock Path.touch to raise PermissionError (simulating write test failure)
    def mock_touch(self, **kwargs):
        raise PermissionError("Cannot touch this")
    
    monkeypatch.setattr("pathlib.Path.touch", mock_touch)
    monkeypatch.setattr("pathlib.Path.mkdir", lambda *args, **kwargs: None) # mkdir succeeds
    
    window._start_download()
    
    assert "Permission denied" in window.setup_msg.text()
    assert "Cannot touch this" in window.setup_msg.text()
