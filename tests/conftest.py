"""Test configuration and shared fixtures."""

import logging
import os
import sys
from pathlib import Path

import pytest

# Force Qt headless mode for CI and macOS test environments.
# This must be set before PyQt6 is imported by any test module.
if os.environ.get("QT_QPA_PLATFORM") is None:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Dynamic backward-compatibility shims for older tests importing legacy namespaces
import types

try:
    import biopro_sdk  # noqa: F401
    import biopro_sdk.host as sdk_host  # noqa: F401
    import biopro_sdk.plugin as sdk_plugin

    sys.modules["biopro.sdk"] = sdk_plugin

    # Shim biopro.sdk.core and its attributes (PluginBase, FunctionalTask, etc.)
    import biopro_sdk.plugin.analysis as analysis
    import biopro_sdk.plugin.base as base
    import biopro_sdk.plugin.managed_task as mt
    import biopro_sdk.plugin.state as state

    sdk_core_shim = types.ModuleType("biopro.sdk.core")
    for mod in [base, analysis, state, mt]:
        for attr in dir(mod):
            if not attr.startswith("__"):
                setattr(sdk_core_shim, attr, getattr(mod, attr))
    sys.modules["biopro.sdk.core"] = sdk_core_shim
    sys.modules["biopro.sdk.core.base"] = base
    sys.modules["biopro.sdk.core.analysis"] = analysis
    sys.modules["biopro.sdk.core.state"] = state
    import biopro_sdk.plugin.interfaces as interfaces

    sys.modules["biopro.sdk.core.interfaces"] = interfaces

    # Shim biopro.core.trust_manager, trust_path, and trust_overrides
    import biopro_sdk.host.trust_manager as tm
    import biopro_sdk.host.trust_overrides as to
    import biopro_sdk.host.trust_path as tp

    sys.modules["biopro.core.trust_manager"] = tm
    sys.modules["biopro.core.trust_path"] = tp
    sys.modules["biopro.core.trust_overrides"] = to
except ImportError:
    pass

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")


# Pytest markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "qt: mark test as requiring Qt/QApplication")


def pytest_sessionfinish(session, exitstatus):
    """Exit cleanly to avoid PyQt6 teardown segfaults on macOS.

    PyQt6 on macOS can segfault during cleanup when destroying the QApplication.
    This hook lets pytest exit before C++ destructors run.
    """
    import os

    os._exit(exitstatus)


# Fixtures for common test setup


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Provide a temporary config directory for tests."""
    config_dir = tmp_path / ".biopro" / "plugin_configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Mock the config directory location
    monkeypatch.setenv("HOME", str(tmp_path.parent))

    yield config_dir


@pytest.fixture
def cleanup_plugin_configs():
    """Clean up plugin configs after test."""
    yield

    # Cleanup: remove test config files
    config_base = Path.home() / ".biopro" / "plugin_configs"
    if config_base.exists():
        for file in config_base.glob("*test*.json"):
            file.unlink(missing_ok=True)
