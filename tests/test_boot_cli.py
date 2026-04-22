import sys
import subprocess
from pathlib import Path

def test_ai_server_cli_mode(monkeypatch):
    """Verify that the 'ai-server' command is correctly handled in __main__.py."""
    import importlib
    import biopro.__main__
    
    import types
    mock_main_called = False
    
    mock_lib = types.ModuleType("llama_cpp")
    mock_server = types.ModuleType("llama_cpp.server")
    mock_main = types.ModuleType("llama_cpp.server.__main__")
    
    def mock_main_fn():
        nonlocal mock_main_called
        mock_main_called = True
        
    mock_main.main = mock_main_fn
    
    # Mock both the parent and the leaf to satisfy the 'import x.y.z' chain
    monkeypatch.setitem(sys.modules, "llama_cpp", mock_lib)
    monkeypatch.setitem(sys.modules, "llama_cpp.server", mock_server)
    monkeypatch.setitem(sys.modules, "llama_cpp.server.__main__", mock_main)
    
    # Setup sys.argv
    original_argv = sys.argv
    sys.argv = ["biopro", "ai-server", "--model", "test.gguf"]
    
    try:
        # Reload to ensure we have the version with ai-server handling
        importlib.reload(biopro.__main__)
        # We need to mock setup_logging to avoid creating files
        monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))
        
        biopro.__main__.main()
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv
        
    assert mock_main_called is True

def test_sdk_cli_mode(monkeypatch):
    """Verify that the 'sdk' command is correctly handled in __main__.py."""
    mock_sdk_main_called = False
    
    class MockSDKModule:
        @staticmethod
        def main():
            nonlocal mock_sdk_main_called
            mock_sdk_main_called = True
            
    monkeypatch.setitem(sys.modules, "biopro.sdk.sdk_cli", MockSDKModule)
    
    original_argv = sys.argv
    sys.argv = ["biopro", "sdk", "test"]
    
    try:
        from biopro.__main__ import main
        monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))
        main()
    except SystemExit:
        pass
    finally:
        sys.argv = original_argv
        
    assert mock_sdk_main_called is True
