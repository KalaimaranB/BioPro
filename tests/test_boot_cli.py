import sys
from pathlib import Path
from typing import Any

import pytest

# Test-specific timeout constant for smoke test validation
TEST_SMOKE_TIMEOUT_MS = 100


def test_smoke_test_timeout_no_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that smoke test returns failure when data_ready signal never emits."""
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import QApplication, QWidget

    # Mock panel class that has data_ready but never emits it
    class MockPanel(QWidget):
        data_ready = pyqtSignal()

        def __init__(self) -> None:
            super().__init__()

        def load_workflow(self, *args: Any, **kwargs: Any) -> None:
            # Simulate loading but never emit data_ready
            pass

    # Mock ModuleManager
    class MockModuleManager:
        def reload_modules(self) -> None:
            pass

        def trust_module(self, module_id: str) -> None:
            pass

        def load_module_ui(self, module_id: str) -> type[MockPanel]:
            return MockPanel

    # Mock NetworkUpdater
    class MockNetworkUpdater:
        plugin_dir = Path("/tmp/plugins")
        registry_url = "https://example.com/test-registry.json"

        def fetch_remote_registry(self, url: str) -> dict[str, Any]:
            return {"plugins": {"test_plugin": {"version": "1.0.0"}}}

        def install_plugin(self, plugin_id: str, plugin_info: dict[str, Any]) -> tuple[bool, str]:
            return True, "Success"

    # Mock PackageManager
    class MockPackageManager:
        def resolve_and_install_all(self, deps: dict[str, str], plugin_dir: Path) -> None:
            pass

    monkeypatch.setattr("biopro.core.module_manager.ModuleManager", MockModuleManager)
    monkeypatch.setattr("biopro.core.network_updater.NetworkUpdater", MockNetworkUpdater)
    monkeypatch.setattr("biopro.core.package_manager.PackageManager", MockPackageManager)
    monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))

    # Significantly reduce timeout for testing
    monkeypatch.setattr("biopro.__main__.SMOKE_TEST_TIMEOUT_MS", TEST_SMOKE_TIMEOUT_MS)

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


def test_smoke_test_panel_ready_without_data_ready(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: C901
    """Verify that smoke test succeeds when panel_ready signal emits but data_ready is absent."""
    from PyQt6.QtCore import QTimer, pyqtSignal
    from PyQt6.QtWidgets import QApplication, QWidget

    # Track load_workflow invocations
    load_workflow_calls: list[Any] = []

    # Mock panel class that has panel_ready but NOT data_ready
    class MockPanel(QWidget):
        panel_ready = pyqtSignal()

        def __init__(self) -> None:
            super().__init__()

        def begin_async_init(self) -> None:
            # Emit panel_ready asynchronously to test race condition fix
            QTimer.singleShot(0, self.panel_ready.emit)

        def load_workflow(self, *args: Any, **kwargs: Any) -> None:
            load_workflow_calls.append((args, kwargs))

    # Mock ModuleManager
    class MockModuleManager:
        def reload_modules(self) -> None:
            pass

        def trust_module(self, module_id: str) -> None:
            pass

        def load_module_ui(self, module_id: str) -> type[MockPanel]:
            return MockPanel

    # Mock NetworkUpdater
    class MockNetworkUpdater:
        plugin_dir = Path("/tmp/plugins")
        registry_url = "https://example.com/test-registry.json"

        def fetch_remote_registry(self, url: str) -> dict[str, Any]:
            return {"plugins": {"test_plugin": {"version": "1.0.0"}}}

        def install_plugin(self, plugin_id: str, plugin_info: dict[str, Any]) -> tuple[bool, str]:
            return True, "Success"

    # Mock PackageManager
    class MockPackageManager:
        def resolve_and_install_all(self, deps: dict[str, str], plugin_dir: Path) -> None:
            pass

    monkeypatch.setattr("biopro.core.module_manager.ModuleManager", MockModuleManager)
    monkeypatch.setattr("biopro.core.network_updater.NetworkUpdater", MockNetworkUpdater)
    monkeypatch.setattr("biopro.core.package_manager.PackageManager", MockPackageManager)
    monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))

    # Significantly reduce timeout for testing
    monkeypatch.setattr("biopro.__main__.SMOKE_TEST_TIMEOUT_MS", TEST_SMOKE_TIMEOUT_MS)

    original_argv = sys.argv
    sys.argv = ["biopro", "--smoke-test=test_plugin", "/tmp/test_data.fcs"]

    try:
        from biopro.__main__ import _run_smoke_test

        exit_code = _run_smoke_test(sys.argv)

        # Should return 0 because panel_ready emitted and load_workflow was called
        assert exit_code == 0
        # load_workflow should have been called exactly once
        assert len(load_workflow_calls) == 1
    finally:
        sys.argv = original_argv
        # Clean up QApplication instance
        app = QApplication.instance()
        if app:
            app.quit()


def test_smoke_test_panel_ready_load_workflow_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that smoke test returns failure when load_workflow raises an exception on a panel lacking data_ready."""
    from PyQt6.QtCore import QTimer, pyqtSignal
    from PyQt6.QtWidgets import QApplication, QWidget

    # Mock panel class that has panel_ready but NOT data_ready, and load_workflow raises
    class MockPanel(QWidget):
        panel_ready = pyqtSignal()

        def __init__(self) -> None:
            super().__init__()

        def begin_async_init(self) -> None:
            # Emit panel_ready asynchronously to test race condition fix
            QTimer.singleShot(0, self.panel_ready.emit)

        def load_workflow(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Simulated load_workflow failure")

    # Mock ModuleManager
    class MockModuleManager:
        def reload_modules(self) -> None:
            pass

        def trust_module(self, module_id: str) -> None:
            pass

        def load_module_ui(self, module_id: str) -> type[MockPanel]:
            return MockPanel

    # Mock NetworkUpdater
    class MockNetworkUpdater:
        plugin_dir = Path("/tmp/plugins")
        registry_url = "https://example.com/test-registry.json"

        def fetch_remote_registry(self, url: str) -> dict[str, Any]:
            return {"plugins": {"test_plugin": {"version": "1.0.0"}}}

        def install_plugin(self, plugin_id: str, plugin_info: dict[str, Any]) -> tuple[bool, str]:
            return True, "Success"

    # Mock PackageManager
    class MockPackageManager:
        def resolve_and_install_all(self, deps: dict[str, str], plugin_dir: Path) -> None:
            pass

    monkeypatch.setattr("biopro.core.module_manager.ModuleManager", MockModuleManager)
    monkeypatch.setattr("biopro.core.network_updater.NetworkUpdater", MockNetworkUpdater)
    monkeypatch.setattr("biopro.core.package_manager.PackageManager", MockPackageManager)
    monkeypatch.setattr("biopro.__main__.setup_logging", lambda: Path("/tmp/biopro.log"))

    # Significantly reduce timeout for testing
    monkeypatch.setattr("biopro.__main__.SMOKE_TEST_TIMEOUT_MS", TEST_SMOKE_TIMEOUT_MS)

    original_argv = sys.argv
    sys.argv = ["biopro", "--smoke-test=test_plugin", "/tmp/test_data.fcs"]

    try:
        from biopro.__main__ import _run_smoke_test

        exit_code = _run_smoke_test(sys.argv)

        # Should return 1 because load_workflow raised an exception
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
