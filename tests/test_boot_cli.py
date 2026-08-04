import sys
from pathlib import Path


def test_smoke_test_timeout_no_signal(monkeypatch):
    """Verify that smoke test returns failure when data_ready signal never emits."""
    from PyQt6.QtWidgets import QApplication, QWidget

    # Mock panel class that has data_ready but never emits it
    class MockPanel(QWidget):
        def __init__(self):
            super().__init__()
            from PyQt6.QtCore import pyqtSignal

            self.data_ready = pyqtSignal()

        def load_workflow(self, *args, **kwargs):
            # Simulate loading but never emit data_ready
            pass

    # Mock ModuleManager
    class MockModuleManager:
        def reload_modules(self):
            pass

        def trust_module(self, module_id):
            pass

        def load_module_ui(self, module_id):
            return MockPanel

    # Mock NetworkUpdater
    class MockNetworkUpdater:
        plugin_dir = Path("/tmp/plugins")

        def fetch_remote_registry(self, url):
            return {"plugins": {"test_plugin": {"version": "1.0.0"}}}

        def install_plugin(self, plugin_id, plugin_info):
            return True, "Success"

    # Mock PackageManager
    class MockPackageManager:
        def resolve_and_install_all(self, deps, plugin_dir):
            pass

    monkeypatch.setattr("biopro.core.module_manager.ModuleManager", MockModuleManager)
    monkeypatch.setattr("biopro.core.network_updater.NetworkUpdater", MockNetworkUpdater)
    monkeypatch.setattr("biopro.core.package_manager.PackageManager", MockPackageManager)
    monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))

    # Significantly reduce timeout for testing
    monkeypatch.setattr("biopro.__main__.SMOKE_TEST_TIMEOUT_MS", 100)

    original_argv = sys.argv
    sys.argv = ["biopro", "--smoke-test=test_plugin", "/tmp/test_data.fcs"]

    try:
        from biopro.__main__ import _run_smoke_test

        exit_code = _run_smoke_test(sys.argv)

        # Should return 1 because data_ready never emitted
        assert exit_code == 1
    finally:
        sys.argv = original_argv
        # Clean up QApplication instance
        app = QApplication.instance()
        if app:
            app.quit()


def test_ai_server_cli_mode(monkeypatch):
    """Verify that the 'ai-server' command is correctly handled in __main__.py."""
    import importlib
    import types

    import biopro.__main__

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

    monkeypatch.setitem(sys.modules, "biopro_sdk.sdk_cli", MockSDKModule)

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
