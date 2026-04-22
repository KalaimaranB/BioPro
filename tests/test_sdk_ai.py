import pytest
from PyQt6.QtCore import QCoreApplication
from biopro.sdk.core.ai import AIAssistant, AIServerManager

class MockAIAssistant(AIAssistant):
    def ask_question(self, prompt: str) -> str:
        return f"Response to: {prompt}"

def test_ai_server_manager_initialization():
    manager = AIServerManager()
    assert manager.logger is not None
    assert manager.model_path == "models/gemma4.gguf"

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
