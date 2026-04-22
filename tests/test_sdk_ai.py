import pytest
import os
import sys
from PyQt6.QtCore import QCoreApplication
from biopro.sdk.core.ai import AIAssistant, AIServerManager

class MockAIAssistant(AIAssistant):
    def ask_question(self, prompt: str) -> str:
        return f"Response to: {prompt}"

def test_ai_server_manager_initialization():
    from pathlib import Path
    manager = AIServerManager()
    assert manager.logger is not None
    expected_path = str(Path.home() / ".biopro" / "models" / "gemma4.gguf")
    assert manager.model_path == expected_path

def test_ai_server_manager_download_prompt(qapp, monkeypatch):
    manager = AIServerManager()
    
    # Mock os.path.exists to simulate missing model
    monkeypatch.setattr("os.path.exists", lambda path: False)
    
    prompt_emitted = False
    def on_prompt_download():
        nonlocal prompt_emitted
        prompt_emitted = True
        
    manager.signals.prompt_download.connect(on_prompt_download)
    
    manager.start_server()
    QCoreApplication.processEvents()
    
    assert prompt_emitted is True

def test_ai_assistant_interface():
    assistant = MockAIAssistant()
    assert assistant.ask_question("Hello") == "Response to: Hello"

def test_model_path_persistence():
    """Verify that AIServerManager uses the persistent home directory path."""
    manager = AIServerManager()
    assert ".biopro" in manager.model_path
    assert "models" in manager.model_path
    assert os.path.isabs(manager.model_path)

def test_start_server_absolute_path(monkeypatch):
    """Verify that start_server uses absolute paths for the model command."""
    import subprocess
    import requests
    manager = AIServerManager(model_path="relative/path/to/model.gguf")
    
    # Mock os.path.exists to return True for our fake model
    monkeypatch.setattr("os.path.exists", lambda x: True)
    
    # Mock socket to simulate port 8080 is free
    class MockSocket:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def connect_ex(self, addr): return 1 # Port free
    monkeypatch.setattr("socket.socket", lambda *args: MockSocket())
    
    # Capture subprocess.Popen calls
    popen_args = []
    def mock_popen(cmd, **kwargs):
        popen_args.append(cmd)
        # Return a mock process that is "running"
        class MockProcess:
            def poll(self): return None
            def terminate(self): pass
        return MockProcess()
        
    monkeypatch.setattr("subprocess.Popen", mock_popen)
    # Mock requests.get to simulate server ready
    class MockResponse:
        status_code = 200
    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse())
    
    manager.start_server()
    
    # Verify that the model path in the command was made absolute
    assert len(popen_args) > 0
    cmd = popen_args[0]
    model_arg_idx = cmd.index("--model") + 1
    assert os.path.isabs(cmd[model_arg_idx])
    assert "relative/path/to/model.gguf" in cmd[model_arg_idx]
